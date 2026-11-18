"""Java parser: Extracts packages, imports, classes, interfaces, methods, annotations."""
import re
from typing import List
from app.parsers import BaseParser, ParseResult, ParsedFunction, ParsedClass, ParsedImport


class JavaParser(BaseParser):
    def parse(self, content: str, file_path: str) -> ParseResult:
        lines = content.splitlines()
        loc = len(lines)
        result = ParseResult(language="java", file_path=file_path, total_loc=loc)

        if not content.strip():
            return result

        # 1. Imports
        import_matches = re.finditer(r"""import\s+(?:static\s+)?([A-Za-z0-9_$.*]+)\s*;""", content)
        for m in import_matches:
            pkg = m.group(1)
            start_line = content[: m.start()].count("\n") + 1
            parts = pkg.split(".")
            name = parts[-1]
            module = ".".join(parts[:-1]) if len(parts) > 1 else pkg
            result.imports.append(ParsedImport(module=module, names=[name], start_line=start_line))

        # 2. Classes and Interfaces
        class_matches = re.finditer(
            r"""(?:(?:public|protected|private|abstract|final|static)\s+)*(class|interface|enum)\s+([A-Za-z0-9_$]+)(?:<[^>]+>)?(?:\s+extends\s+([^{]+))?(?:\s+implements\s+([^{]+))?\s*\{""",
            content,
        )
        for m in class_matches:
            kind = m.group(1)
            name = m.group(2)
            extends_raw = m.group(3) or ""
            implements_raw = m.group(4) or ""
            bases = [b.strip() for b in (extends_raw + "," + implements_raw).split(",") if b.strip()]
            start_line = content[: m.start()].count("\n") + 1
            end_line = self._find_closing_brace_line(content, m.end() - 1, start_line)
            cls_content = "\n".join(lines[start_line - 1 : end_line])

            parsed_class = ParsedClass(
                name=f"{kind} {name}",
                start_line=start_line,
                end_line=end_line,
                base_classes=bases,
                content=cls_content,
            )

            # Parse methods inside this class content
            parsed_class.methods = self._extract_java_methods(cls_content, start_line)
            result.classes.append(parsed_class)
            result.functions.extend(parsed_class.methods)

        if result.functions:
            comps = [f.cyclomatic_complexity for f in result.functions]
            result.average_complexity = round(sum(comps) / len(comps), 2)
            result.max_complexity = max(comps)

        return result

    def _extract_java_methods(self, class_code: str, class_start_line: int) -> List[ParsedFunction]:
        methods = []
        method_pattern = re.finditer(
            r"""(?:(?:public|protected|private|static|final|abstract|synchronized)\s+)+([A-Za-z0-9_<>[\]]+)\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)\s*(?:throws\s+[^{;]+)?(\{)""",
            class_code,
        )
        lines = class_code.splitlines()

        for m in method_pattern:
            return_type = m.group(1)
            name = m.group(2)
            params_raw = m.group(3)
            params = [p.strip() for p in params_raw.split(",") if p.strip()]

            rel_start = class_code[: m.start()].count("\n") + 1
            abs_start = class_start_line + rel_start - 1
            abs_end = self._find_closing_brace_line(class_code, m.end() - 1, abs_start)
            method_code = "\n".join(lines[rel_start - 1 : (rel_start - 1 + (abs_end - abs_start + 1))])

            complexity = self._calculate_java_complexity(method_code)

            methods.append(
                ParsedFunction(
                    name=name,
                    start_line=abs_start,
                    end_line=abs_end,
                    parameters=params,
                    return_type=return_type,
                    cyclomatic_complexity=complexity,
                    content=method_code,
                )
            )
        return methods

    def _find_closing_brace_line(self, content: str, open_brace_idx: int, start_line: int) -> int:
        depth = 0
        in_string = False
        str_char = ""
        lines_count = start_line

        for i in range(open_brace_idx, len(content)):
            ch = content[i]
            if ch == "\n":
                lines_count += 1
            if in_string:
                if ch == str_char and content[i - 1] != "\\":
                    in_string = False
            else:
                if ch in ('"', "'"):
                    in_string = True
                    str_char = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return lines_count
        return lines_count

    def _calculate_java_complexity(self, code: str) -> int:
        keywords = [
            r"\bif\b", r"\belse\s+if\b", r"\bfor\b", r"\bwhile\b",
            r"\bcase\b", r"\bcatch\b", r"&&", r"\|\|", r"\?[^:]+:"
        ]
        score = 1
        for kw in keywords:
            score += len(re.findall(kw, code))
        return score
