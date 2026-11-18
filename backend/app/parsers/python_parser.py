"""Python AST-based parser with syntax analysis and cyclomatic complexity."""
import ast
import logging
from typing import List
from app.parsers import BaseParser, ParseResult, ParsedFunction, ParsedClass, ParsedImport

logger = logging.getLogger("codesage.parser.python")


class ComplexityVisitor(ast.NodeVisitor):
    """Computes cyclomatic complexity for Python AST nodes."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # 'and' or 'or' each add a decision path
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)


class PythonParser(BaseParser):
    def parse(self, content: str, file_path: str) -> ParseResult:
        lines = content.splitlines()
        loc = len(lines)
        result = ParseResult(language="python", file_path=file_path, total_loc=loc)

        if not content.strip():
            return result

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as se:
            result.errors.append(f"SyntaxError at line {se.lineno}: {se.msg}")
            return result
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            return result

        # 1. Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(
                        ParsedImport(
                            module=alias.name,
                            names=[alias.name],
                            alias=alias.asname,
                            start_line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                result.imports.append(
                    ParsedImport(
                        module=module,
                        names=names,
                        start_line=node.lineno,
                    )
                )

        # 2. Extract classes and standalone functions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls = self._parse_class(node, lines)
                result.classes.append(cls)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = self._parse_function(node, lines)
                result.functions.append(fn)

        # Compute summary complexity
        all_funcs = list(result.functions)
        for c in result.classes:
            all_funcs.extend(c.methods)

        if all_funcs:
            complexities = [f.cyclomatic_complexity for f in all_funcs]
            result.average_complexity = round(sum(complexities) / len(complexities), 2)
            result.max_complexity = max(complexities)

        return result

    def _parse_class(self, node: ast.ClassDef, lines: List[str]) -> ParsedClass:
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{ast.unparse(base.value)}.{base.attr}")

        docstring = ast.get_docstring(node)
        content = "\n".join(lines[start_line - 1 : end_line])

        parsed_cls = ParsedClass(
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            base_classes=bases,
            docstring=docstring,
            content=content,
        )

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._parse_function(item, lines)
                parsed_cls.methods.append(method)

        return parsed_cls

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, lines: List[str]) -> ParsedFunction:
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        params = [arg.arg for arg in node.args.args]
        return_type = ast.unparse(node.returns) if node.returns else None
        docstring = ast.get_docstring(node)
        content = "\n".join(lines[start_line - 1 : end_line])

        visitor = ComplexityVisitor()
        visitor.visit(node)

        return ParsedFunction(
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            parameters=params,
            return_type=return_type,
            docstring=docstring,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            cyclomatic_complexity=visitor.complexity,
            content=content,
        )
