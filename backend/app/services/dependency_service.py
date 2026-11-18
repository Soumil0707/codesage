"""Dependency graph analysis service: NetworkX integration, circular dependency detection, and React Flow layout."""
import os
import networkx as nx
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.repository import SourceFile
from app.models.analysis import Dependency, DependencyType
from app.parsers import ParserFactory


class DependencyService:
    @classmethod
    async def build_and_save_dependencies(cls, version_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Extract all imports from SourceFiles in the version, resolve targets, save to MySQL."""
        # Clean previous dependencies for this version
        await db.execute(delete(Dependency).where(Dependency.version_id == version_id))

        stmt = select(SourceFile).where(SourceFile.version_id == version_id)
        files = (await db.execute(stmt)).scalars().all()

        file_map: Dict[str, SourceFile] = {f.file_path: f for f in files}
        all_file_paths = set(file_map.keys())

        dependencies_to_insert: List[Dependency] = []
        g = nx.DiGraph()

        # Add all files as nodes
        for f in files:
            g.add_node(f.file_path, language=f.language, loc=f.loc, name=f.file_name)

        for f in files:
            parser = ParserFactory.get_parser(f.language)
            if not parser:
                continue

            parse_result = parser.parse(f.content or "", f.file_path)
            for imp in parse_result.imports:
                target_file, is_ext = cls._resolve_import_to_file(imp.module, f.file_path, all_file_paths, f.language)

                dep = Dependency(
                    version_id=version_id,
                    source_file=f.file_path,
                    target_file=target_file,
                    source_name=f.file_name,
                    target_name=imp.module,
                    dependency_type=DependencyType.IMPORT,
                    is_external=is_ext,
                )
                dependencies_to_insert.append(dep)

                if target_file and not is_ext and target_file in all_file_paths:
                    g.add_edge(f.file_path, target_file, module=imp.module)

        for dep in dependencies_to_insert:
            db.add(dep)
        await db.commit()

        # Find circular dependencies
        cycles = list(nx.simple_cycles(g))
        return {
            "total_dependencies": len(dependencies_to_insert),
            "internal_edges": g.number_of_edges(),
            "nodes_count": g.number_of_nodes(),
            "circular_cycles": cycles,
        }

    @classmethod
    def _resolve_import_to_file(
        cls,
        module: str,
        current_file: str,
        all_paths: set,
        language: str,
    ) -> tuple[Optional[str], bool]:
        """Attempt to resolve an import path to an internal source file."""
        if not module:
            return None, True

        cur_dir = os.path.dirname(current_file)

        if language in ("javascript", "typescript", "jsx", "tsx"):
            # Relative import: ./foo or ../foo
            if module.startswith("."):
                candidate_base = os.path.normpath(os.path.join(cur_dir, module)).replace("\\", "/")
                for ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
                    cand = candidate_base + ext
                    if cand in all_paths:
                        return cand, False
            return None, True

        elif language == "python":
            # Direct relative or package match
            parts = module.split(".")
            # try direct path match
            rel_path = "/".join(parts) + ".py"
            for p in all_paths:
                if p.endswith(rel_path) or p.endswith("/" + rel_path):
                    return p, False
            # Check init.py
            init_path = "/".join(parts) + "/__init__.py"
            for p in all_paths:
                if p.endswith(init_path):
                    return p, False
            return None, True

        elif language == "java":
            java_path = module.replace(".", "/") + ".java"
            for p in all_paths:
                if p.endswith(java_path):
                    return p, False
            return None, True

        return None, True

    @classmethod
    async def get_react_flow_graph(cls, version_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Construct React Flow formatted nodes and edges layout with circular dependency highlighting."""
        # 1. Fetch dependencies and source files
        f_stmt = select(SourceFile).where(SourceFile.version_id == version_id)
        files = (await db.execute(f_stmt)).scalars().all()

        d_stmt = select(Dependency).where(
            Dependency.version_id == version_id,
            Dependency.target_file != None,
            Dependency.is_external == False,
        )
        deps = (await db.execute(d_stmt)).scalars().all()

        g = nx.DiGraph()
        for f in files:
            g.add_node(f.file_path, label=f.file_name, language=f.language, loc=f.loc)
        for d in deps:
            if d.target_file:
                g.add_edge(d.source_file, d.target_file)

        cycles = list(nx.simple_cycles(g))
        cycle_edges = set()
        for cycle in cycles:
            for i in range(len(cycle)):
                u = cycle[i]
                v = cycle[(i + 1) % len(cycle)]
                cycle_edges.add((u, v))

        # Spring/circular layout calculation for React Flow coordinates
        if len(g.nodes) > 0:
            try:
                pos = nx.spring_layout(g, k=150, iterations=50, scale=800)
            except Exception:
                pos = {node: (i * 120, (i % 5) * 80) for i, node in enumerate(g.nodes)}
        else:
            pos = {}

        nodes = []
        for file_path in g.nodes:
            coord = pos.get(file_path, (0, 0))
            f_info = next((f for f in files if f.file_path == file_path), None)
            loc = f_info.loc if f_info else 0
            lang = f_info.language if f_info else "unknown"
            file_name = f_info.file_name if f_info else os.path.basename(file_path)

            nodes.append({
                "id": file_path,
                "type": "codeFileNode",
                "position": {"x": int(coord[0] + 500), "y": int(coord[1] + 400)},
                "data": {
                    "label": file_name,
                    "filePath": file_path,
                    "language": lang,
                    "loc": loc,
                    "inDegree": g.in_degree(file_path) if file_path in g else 0,
                    "outDegree": g.out_degree(file_path) if file_path in g else 0,
                },
            })

        edges = []
        for i, (u, v) in enumerate(g.edges):
            is_circular = (u, v) in cycle_edges
            edges.append({
                "id": f"edge_{i}_{u}_{v}",
                "source": u,
                "target": v,
                "animated": is_circular,
                "style": {"stroke": "#ef4444" if is_circular else "#6366f1", "strokeWidth": 2},
                "data": {"isCircular": is_circular},
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "circular_dependencies": cycles,
            "metrics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "circular_count": len(cycles),
            },
        }
