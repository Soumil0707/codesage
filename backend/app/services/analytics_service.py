"""Developer Analytics Service: Measured metrics, language breakdown, complexity distribution, and dependency health."""
import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.repository import Repository, RepositoryVersion, SourceFile
from app.models.analysis import AnalysisReport, AnalysisFinding, Dependency
from app.services.dependency_service import DependencyService
from app.parsers import ParserFactory


class AnalyticsService:
    @classmethod
    async def get_dashboard(cls, repository_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Aggregate comprehensive repository analytics."""
        # 1. Fetch current version
        v_stmt = select(RepositoryVersion).where(
            RepositoryVersion.repository_id == repository_id,
            RepositoryVersion.is_current == True,
        )
        version = (await db.execute(v_stmt)).scalars().first()

        if not version:
            return {
                "repository_id": repository_id,
                "total_files": 0,
                "total_loc": 0,
                "languages": [],
                "avg_complexity": 0.0,
                "max_complexity": 0,
                "complexity_details": [],
                "dependency_health": None,
                "issue_counts": {},
                "recent_analyses": [],
            }

        # 2. Language Breakdown
        lang_stats = []
        if version.language_stats:
            try:
                stats_dict = json.loads(version.language_stats)
                total_loc = max(version.total_loc, 1)
                for lang, data in stats_dict.items():
                    pct = round((data["loc"] / total_loc) * 100, 1)
                    lang_stats.append({
                        "language": lang,
                        "file_count": data["files"],
                        "loc": data["loc"],
                        "percentage": pct,
                    })
                lang_stats.sort(key=lambda x: x["loc"], reverse=True)
            except Exception:
                pass

        # 3. Complexity Metrics
        f_stmt = select(SourceFile).where(SourceFile.version_id == version.id)
        files = (await db.execute(f_stmt)).scalars().all()

        complexity_details = []
        all_complexities = []

        for f in files:
            parser = ParserFactory.get_parser(f.language)
            if parser and f.content:
                parsed = parser.parse(f.content, f.file_path)
                for fn in parsed.functions:
                    all_complexities.append(fn.cyclomatic_complexity)
                    if fn.cyclomatic_complexity >= 5:
                        complexity_details.append({
                            "file_path": f.file_path,
                            "function_name": fn.name,
                            "cyclomatic_complexity": fn.cyclomatic_complexity,
                        })

        avg_comp = round(sum(all_complexities) / len(all_complexities), 2) if all_complexities else 1.0
        max_comp = max(all_complexities) if all_complexities else 1
        complexity_details.sort(key=lambda x: x["cyclomatic_complexity"], reverse=True)

        # 4. Dependency Health
        d_stmt = select(Dependency).where(Dependency.version_id == version.id)
        deps = (await db.execute(d_stmt)).scalars().all()
        internal_count = sum(1 for d in deps if not d.is_external)
        external_count = sum(1 for d in deps if d.is_external)

        graph_data = await DependencyService.get_react_flow_graph(version.id, db)
        circular_groups = graph_data.get("circular_dependencies", [])

        dep_health = {
            "total_dependencies": len(deps),
            "internal_dependencies": internal_count,
            "external_dependencies": external_count,
            "circular_dependencies": len(circular_groups),
            "circular_dependency_groups": circular_groups,
        }

        # 5. Issue counts from latest AnalysisReport
        rep_stmt = (
            select(AnalysisReport)
            .where(AnalysisReport.repository_id == repository_id)
            .options(selectinload(AnalysisReport.findings))
            .order_by(desc(AnalysisReport.created_at))
        )
        reports = (await db.execute(rep_stmt)).scalars().all()
        issue_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        if reports:
            latest = reports[0]
            for f in latest.findings:
                sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                if sev in issue_counts:
                    issue_counts[sev] += 1

        return {
            "repository_id": repository_id,
            "total_files": version.file_count,
            "total_loc": version.total_loc,
            "languages": lang_stats,
            "avg_complexity": avg_comp,
            "max_complexity": max_comp,
            "complexity_details": complexity_details[:10],
            "dependency_health": dep_health,
            "issue_counts": issue_counts,
            "recent_analyses": reports[:5],
        }
