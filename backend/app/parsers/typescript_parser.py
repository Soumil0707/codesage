"""TypeScript parser: Extends JS parser with interfaces, types, decorators, enums."""
import re
from typing import List
from app.parsers.javascript_parser import JavaScriptParser
from app.parsers import ParseResult, ParsedClass, ParsedFunction, ParsedImport


class TypeScriptParser(JavaScriptParser):
    def parse(self, content: str, file_path: str) -> ParseResult:
        result = super().parse(content, file_path)
        result.language = "typescript"
        lines = content.splitlines()

        # Extract interfaces & type aliases as classes for code structure mapping
        interfaces = re.finditer(
            r"""(?:export\s+)?interface\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([^{]+))?\s*\{""",
            content,
        )
        for m in interfaces:
            name = m.group(1)
            bases = [b.strip() for b in (m.group(2) or "").split(",") if b.strip()]
            start_line = content[: m.start()].count("\n") + 1
            end_line = self._find_closing_brace_line(content, m.end() - 1, start_line)
            cls_content = "\n".join(lines[start_line - 1 : end_line])
            result.classes.append(
                ParsedClass(
                    name=f"interface {name}",
                    start_line=start_line,
                    end_line=end_line,
                    base_classes=bases,
                    content=cls_content,
                )
            )

        # Extract enums
        enums = re.finditer(r"""(?:export\s+)?enum\s+([A-Za-z0-9_$]+)\s*\{""", content)
        for m in enums:
            name = m.group(1)
            start_line = content[: m.start()].count("\n") + 1
            end_line = self._find_closing_brace_line(content, m.end() - 1, start_line)
            cls_content = "\n".join(lines[start_line - 1 : end_line])
            result.classes.append(
                ParsedClass(
                    name=f"enum {name}",
                    start_line=start_line,
                    end_line=end_line,
                    content=cls_content,
                )
            )

        return result
