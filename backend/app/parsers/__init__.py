"""Multi-language Code Parsers for Python, JavaScript, TypeScript, and Java."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class ParsedFunction:
    name: str
    start_line: int
    end_line: int
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    cyclomatic_complexity: int = 1
    content: str = ""
    signature: Optional[str] = None


@dataclass
class ParsedClass:
    name: str
    start_line: int
    end_line: int
    base_classes: List[str] = field(default_factory=list)
    methods: List[ParsedFunction] = field(default_factory=list)
    docstring: Optional[str] = None
    content: str = ""


@dataclass
class ParsedImport:
    module: str
    names: List[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_external: bool = False
    start_line: int = 1


@dataclass
class ParseResult:
    language: str
    file_path: str
    functions: List[ParsedFunction] = field(default_factory=list)
    classes: List[ParsedClass] = field(default_factory=list)
    imports: List[ParsedImport] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_loc: int = 0
    average_complexity: float = 1.0
    max_complexity: int = 1


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse source code content and extract functions, classes, imports, and complexity metrics."""
        pass


class ParserFactory:
    _parsers: Dict[str, BaseParser] = {}

    @classmethod
    def get_parser(cls, language: str) -> Optional[BaseParser]:
        """Obtain parser instance for the requested language."""
        lang = language.lower()
        if lang in cls._parsers:
            return cls._parsers[lang]

        if lang == "python":
            from app.parsers.python_parser import PythonParser
            parser = PythonParser()
        elif lang in ("javascript", "jsx"):
            from app.parsers.javascript_parser import JavaScriptParser
            parser = JavaScriptParser()
        elif lang in ("typescript", "tsx"):
            from app.parsers.typescript_parser import TypeScriptParser
            parser = TypeScriptParser()
        elif lang == "java":
            from app.parsers.java_parser import JavaParser
            parser = JavaParser()
        else:
            return None

        cls._parsers[lang] = parser
        return parser
