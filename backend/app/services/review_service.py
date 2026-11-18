"""Code Review Engine: Hybrid deterministic static analysis combined with AI explanations and refactoring diffs."""
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.repository import RepositoryVersion, SourceFile
from app.models.analysis import (
    AnalysisReport,
    AnalysisFinding,
    ReportType,
    Severity,
    FindingCategory,
    VerificationStatus,
)
from app.parsers import ParserFactory
from app.services.llm_service import LLMService

logger = logging.getLogger("codesage.review")

# Static Security Patterns
SECRET_PATTERNS = [
    (r"(?i)(password|passwd|secret|api_key|apikey|token|auth_key)\s*=\s*['\"][A-Za-z0-9_\-.~+=]{8,}['\"]", "Hardcoded credential or API secret"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token"),
    (r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+", "Hardcoded JSON Web Token (JWT)"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Hardcoded Private Key"),
]

UNSAFE_PATTERNS = [
    (r"(?i)(SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*[\w.]+", "Potential SQL Injection: String concatenation in query"),
    (r"\b(eval|exec)\s*\(", "Dangerous dynamic code execution (eval/exec)"),
    (r"subprocess\.(?:call|Popen|run)\([^)]*shell\s*=\s*True", "Unsafe shell execution with shell=True"),
    (r"(?i)except(?:\s+\w+)?:\s*pass", "Suppressed exception without logging or handling"),
]


class ReviewService:
    @classmethod
    def analyze_static_security(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Scan source code for secrets, SQL injections, and dangerous function patterns."""
        findings = []
        lines = content.splitlines()

        for pattern, desc in SECRET_PATTERNS:
            for m in re.finditer(pattern, content):
                line_no = content[: m.start()].count("\n") + 1
                snippet = lines[line_no - 1] if line_no <= len(lines) else m.group(0)
                findings.append({
                    "file_path": file_path,
                    "start_line": line_no,
                    "end_line": line_no,
                    "severity": Severity.CRITICAL,
                    "category": FindingCategory.SECURITY,
                    "rule_id": "SEC001-HARDCODED-SECRET",
                    "title": "Hardcoded Secret / Credential Detected",
                    "description": f"{desc}. Secrets should be stored in environment variables or a secrets manager.",
                    "suggested_fix": "Extract value into environment variables (e.g. os.getenv or process.env).",
                    "code_snippet": snippet.strip(),
                    "verification_status": VerificationStatus.VERIFIED_DEFECT,
                    "confidence": 0.95,
                })

        for pattern, desc in UNSAFE_PATTERNS:
            for m in re.finditer(pattern, content):
                line_no = content[: m.start()].count("\n") + 1
                snippet = lines[line_no - 1] if line_no <= len(lines) else m.group(0)
                findings.append({
                    "file_path": file_path,
                    "start_line": line_no,
                    "end_line": line_no,
                    "severity": Severity.HIGH,
                    "category": FindingCategory.SECURITY,
                    "rule_id": "SEC002-UNSAFE-PATTERN",
                    "title": desc,
                    "description": f"Detected unsafe pattern: {desc}.",
                    "suggested_fix": "Use parameterized queries or safe APIs without shell execution.",
                    "code_snippet": snippet.strip(),
                    "verification_status": VerificationStatus.VERIFIED_DEFECT,
                    "confidence": 0.90,
                })

        return findings

    @classmethod
    def analyze_static_complexity_and_smells(cls, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        """Evaluate cyclomatic complexity, function length, and code smells via Parser AST."""
        findings = []
        parser = ParserFactory.get_parser(language)
        if not parser:
            return findings

        parsed = parser.parse(content, file_path)

        for fn in parsed.functions:
            # 1. Cyclomatic Complexity Checks
            if fn.cyclomatic_complexity >= 20:
                findings.append({
                    "file_path": file_path,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "severity": Severity.CRITICAL,
                    "category": FindingCategory.COMPLEXITY,
                    "rule_id": "CMP001-EXTREME-COMPLEXITY",
                    "title": f"Excessive Cyclomatic Complexity in `{fn.name}` (Complexity: {fn.cyclomatic_complexity})",
                    "description": f"Function has cyclomatic complexity of {fn.cyclomatic_complexity} (threshold: 20). High branching makes this function error-prone and hard to test.",
                    "suggested_fix": "Decompose into smaller single-responsibility helper functions or use strategy/polymorphism.",
                    "code_snippet": f"{getattr(fn, 'signature', None) or fn.name} - Lines {fn.start_line}-{fn.end_line}",
                    "verification_status": VerificationStatus.VERIFIED_DEFECT,
                    "confidence": 1.0,
                })
            elif fn.cyclomatic_complexity >= 10:
                findings.append({
                    "file_path": file_path,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "severity": Severity.MEDIUM,
                    "category": FindingCategory.COMPLEXITY,
                    "rule_id": "CMP002-HIGH-COMPLEXITY",
                    "title": f"High Cyclomatic Complexity in `{fn.name}` (Complexity: {fn.cyclomatic_complexity})",
                    "description": f"Function branching complexity is {fn.cyclomatic_complexity} (threshold: 10).",
                    "suggested_fix": "Simplify conditional branches and guard clauses.",
                    "code_snippet": f"{getattr(fn, 'signature', None) or fn.name} - Lines {fn.start_line}-{fn.end_line}",
                    "verification_status": VerificationStatus.VERIFIED_DEFECT,
                    "confidence": 0.9,
                })

            # 2. Long Function Smell (> 60 lines)
            fn_len = fn.end_line - fn.start_line + 1
            if fn_len > 60:
                findings.append({
                    "file_path": file_path,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "severity": Severity.LOW,
                    "category": FindingCategory.CODE_SMELL,
                    "rule_id": "SML001-LONG-FUNCTION",
                    "title": f"Long Function Smell in `{fn.name}` ({fn_len} lines)",
                    "description": f"Function is {fn_len} lines long. Long functions often violate Single Responsibility Principle.",
                    "suggested_fix": "Extract cohesive sub-tasks into separate private functions.",
                    "code_snippet": f"{fn.name} ({fn_len} lines)",
                    "verification_status": VerificationStatus.VERIFIED_DEFECT,
                    "confidence": 0.85,
                })

        return findings

    @classmethod
    async def run_review(
        cls,
        repository_id: str,
        version_id: str,
        report_type: ReportType,
        file_paths: Optional[List[str]],
        db: AsyncSession,
    ) -> AnalysisReport:
        """Execute comprehensive deterministic static checks and AI synthesis."""
        report = AnalysisReport(
            repository_id=repository_id,
            version_id=version_id,
            report_type=report_type,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(report)
        await db.flush()

        stmt = select(SourceFile).where(SourceFile.version_id == version_id)
        if file_paths:
            stmt = stmt.where(SourceFile.file_path.in_(file_paths))
        files = (await db.execute(stmt)).scalars().all()

        all_findings: List[AnalysisFinding] = []
        critical_c = 0
        warning_c = 0
        info_c = 0

        for f in files:
            if not f.content:
                continue

            # Deterministic static checks
            sec_findings = cls.analyze_static_security(f.content, f.file_path)
            cmp_findings = cls.analyze_static_complexity_and_smells(f.content, f.file_path, f.language)

            for f_dict in sec_findings + cmp_findings:
                finding = AnalysisFinding(
                    report_id=report.id,
                    file_path=f_dict["file_path"],
                    start_line=f_dict["start_line"],
                    end_line=f_dict["end_line"],
                    severity=f_dict["severity"],
                    category=f_dict["category"],
                    rule_id=f_dict.get("rule_id"),
                    title=f_dict["title"],
                    description=f_dict["description"],
                    suggested_fix=f_dict.get("suggested_fix"),
                    code_snippet=f_dict.get("code_snippet"),
                    verification_status=f_dict["verification_status"],
                    confidence=f_dict["confidence"],
                )
                all_findings.append(finding)

                if finding.severity in (Severity.CRITICAL, Severity.HIGH):
                    critical_c += 1
                elif finding.severity in (Severity.MEDIUM, Severity.LOW):
                    warning_c += 1
                else:
                    info_c += 1

        for f in all_findings:
            db.add(f)

        report.status = "completed"
        report.completed_at = datetime.utcnow()
        report.total_issues = len(all_findings)
        report.critical_count = critical_c
        report.warning_count = warning_c
        report.info_count = info_c
        report.summary = (
            f"Code review completed across {len(files)} files. "
            f"Detected {len(all_findings)} issues: {critical_c} critical/high, "
            f"{warning_c} warnings, {info_c} informational."
        )

        await db.commit()
        await db.refresh(report)
        return report
