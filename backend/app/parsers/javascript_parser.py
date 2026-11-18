"""JavaScript parser with regex-based AST token extraction & complexity calculation."""
import re
from typing import List
from app.parsers import BaseParser, ParseResult, ParsedFunction, ParsedClass, ParsedImport


class JavaScriptParser(BaseParser):
    def parse(self, content: str, file_path: str) -> ParseResult:
        lines = content.splitlines()
        loc = len(lines)
        result = ParseResult(language="javascript", file_path=file_path, total_loc=loc)

        if not content.strip():
            return result

        # 1. Imports: import { a, b } from 'mod'; import x from 'mod'; const x = require('mod');
        import_es6 = re.finditer(
            r"""import\s+(?:(?:\*\s+as\s+(\w+)|([\w\s{},*]+))\s+from\s+)?['"]([^'"]+)['"]""",
            content,
        )
        for m in import_es6:
            line_no = content[: m.start()].count("\n") + 1
            names_raw = m.group(1) or m.group(2) or ""
            module = m.group(3)
            names = [n.strip() for n in re.findall(r"\w+", names_raw) if n.strip() not in ("import", "from", "as", "default")]
            result.imports.append(ParsedImport(module=module, names=names, start_line=line_no))

        require_cjs = re.finditer(
            r"""(?:const|let|var)\s+([\w\s{},]+)\s*=\s*require\(['"]([^'"]+)['"]\)""",
            content,
        )
        for m in require_cjs:
            line_no = content[: m.start()].count("\n") + 1
            names = [n.strip() for n in re.findall(r"\w+", m.group(1))]
            module = m.group(2)
            result.imports.append(ParsedImport(module=module, names=names, start_line=line_no))

        # 2. Classes: class Foo extends Bar { ... }
        class_matches = re.finditer(
            r"""class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?\s*\{""",
            content,
        )
        for m in class_matches:
            name = m.group(1)
            base = [m.group(2)] if m.group(2) else []
            start_line = content[: m.start()].count("\n") + 1
            # Find matching brace
            end_line = self._find_closing_brace_line(content, m.end() - 1, start_line)
            cls_content = "\n".join(lines[start_line - 1 : end_line])
            result.classes.append(
                ParsedClass(
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    base_classes=base,
                    content=cls_content,
                )
            )

        # 3. Functions: function name(), const name = () => {}, async function name()
        fn_pattern = re.finditer(
            r"""(?:(?:export\s+)?(?:default\s+)?(async\s+)?function\s*([A-Za-z0-9_$]*)\s*\(([^)]*)\)|(?:(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(async\s+)?(?:\(([^)]*)\)|([A-Za-z0-9_$]+))\s*=>))""",
            content,
        )
        for m in fn_pattern:
            is_async = bool(m.group(1) or m.group(5))
            name = m.group(2) or m.group(4) or "anonymous"
            params_raw = m.group(3) or m.group(6) or m.group(7) or ""
            params = [p.strip() for p in params_raw.split(",") if p.strip()]
            start_line = content[: m.start()].count("\n") + 1
            end_line = self._find_function_end(content, m.end(), start_line, lines)
            fn_content = "\n".join(lines[start_line - 1 : end_line])

            complexity = self._calculate_js_complexity(fn_content)

            result.functions.append(
                ParsedFunction(
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    parameters=params,
                    is_async=is_async,
                    cyclomatic_complexity=complexity,
                    content=fn_content,
                )
            )

        if result.functions:
            comps = [f.cyclomatic_complexity for f in result.functions]
            result.average_complexity = round(sum(comps) / len(comps), 2)
            result.max_complexity = max(comps)

        return result

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
                if ch in ('"', "'", "`"):
                    in_string = True
                    str_char = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return lines_count
        return lines_count

    def _find_function_end(self, content: str, after_sig_idx: int, start_line: int, lines: List[str]) -> int:
        # Check if function has a body with {
        rest = content[after_sig_idx : after_sig_idx + 200]
        brace_pos = rest.find("{")
        if brace_pos != -1:
            return self._find_closing_brace_line(content, after_sig_idx + brace_pos, start_line)
        # Arrow function single-line expression
        newline_idx = content.find("\n", after_sig_idx)
        if newline_idx != -1:
            return content[:newline_idx].count("\n") + 1
        return len(lines)

    def _calculate_js_complexity(self, code: str) -> int:
        keywords = [
            r"\bif\b", r"\belse\s+if\b", r"\bfor\b", r"\bwhile\b",
            r"\bcase\b", r"\bcatch\b", r"&&", r"\|\|", r"\?\?", r"\?[^:]+:"
        ]
        score = 1
        for kw in keywords:
            score += len(re.findall(kw, code))
        return score
