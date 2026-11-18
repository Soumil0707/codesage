"""Pydantic v2 schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = Field(None, pattern=r"^(light|dark|system)$")
    default_language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    llm_model_preference: Optional[str] = None


class UserSettingsResponse(BaseModel):
    theme: str
    default_language: str
    notifications_enabled: bool
    llm_model_preference: str

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Repository Schemas
# ──────────────────────────────────────────────

class RepoCreateGitHub(BaseModel):
    github_url: str = Field(..., pattern=r"^https?://github\.com/[\w.-]+/[\w.-]+/?$")
    name: Optional[str] = None
    branch: Optional[str] = "main"
    github_token: Optional[str] = None


class RepoResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source: str
    github_url: Optional[str] = None
    primary_language: Optional[str] = None
    total_files: int
    total_loc: int
    indexing_status: str
    last_indexed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RepoDetailResponse(RepoResponse):
    versions: List["VersionResponse"] = []


class VersionResponse(BaseModel):
    id: str
    version_number: int
    commit_sha: Optional[str] = None
    upload_hash: Optional[str] = None
    is_current: bool
    file_count: int
    total_loc: int
    language_stats: Optional[str] = None  # JSON
    created_at: datetime

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    language: str
    content: Optional[str] = None
    size_bytes: int
    loc: int
    is_parseable: bool
    parse_error: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Chat / RAG Schemas
# ──────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    repository_id: str
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: str
    repository_id: str
    title: str
    message_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class Citation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    snippet: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Code Review Schemas
# ──────────────────────────────────────────────

class ReviewRequest(BaseModel):
    repository_id: str
    version_id: Optional[str] = None
    file_paths: Optional[List[str]] = None  # Specific files, or None for all
    review_type: str = Field(default="full_analysis", pattern=r"^(code_review|security_scan|quality_analysis|full_analysis)$")


class FindingResponse(BaseModel):
    id: str
    file_path: str
    start_line: int
    end_line: int
    severity: str
    category: str
    rule_id: Optional[str] = None
    title: str
    description: str
    suggested_fix: Optional[str] = None
    code_snippet: Optional[str] = None
    verification_status: str
    confidence: float

    class Config:
        from_attributes = True


class ReviewReportResponse(BaseModel):
    id: str
    repository_id: str
    report_type: str
    status: str
    summary: Optional[str] = None
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    findings: List[FindingResponse] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Interview Schemas
# ──────────────────────────────────────────────

class InterviewStart(BaseModel):
    repository_id: str
    title: Optional[str] = "Technical Interview"
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")


class InterviewAnswerResponse(BaseModel):
    id: str
    score: float
    max_score: float
    answer_text: Optional[str] = None
    evaluation: Optional[dict] = None
    topics_demonstrated: Optional[List[str]] = None
    topics_missed: Optional[List[str]] = None

    class Config:
        from_attributes = True


class InterviewQuestionResponse(BaseModel):
    id: str
    question_number: int
    difficulty: str
    category: str
    question_text: str
    context_code: Optional[str] = None
    context_file_path: Optional[str] = None
    is_follow_up: bool
    answer: Optional[InterviewAnswerResponse] = None

    class Config:
        from_attributes = True


class InterviewAnswerSubmit(BaseModel):
    answer_text: str = Field(..., min_length=1, max_length=10000)


class InterviewSessionResponse(BaseModel):
    id: str
    title: str
    status: str
    current_difficulty: str
    total_questions: int
    total_score: float
    max_score: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewReportResponse(InterviewSessionResponse):
    topics_covered: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    final_report: Optional[dict] = None
    questions: List[InterviewQuestionResponse] = []


# ──────────────────────────────────────────────
# Documentation Schemas
# ──────────────────────────────────────────────

class DocGenerateRequest(BaseModel):
    repository_id: str
    version_id: Optional[str] = None
    doc_type: str = Field(default="full_docs", pattern=r"^(readme|architecture|api_spec|db_schema|sequence_diagram|component_doc|full_docs)$")


class DocResponse(BaseModel):
    id: str
    repository_id: str
    doc_type: str
    title: str
    content_markdown: str
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Analytics Schemas
# ──────────────────────────────────────────────

class LanguageBreakdown(BaseModel):
    language: str
    file_count: int
    loc: int
    percentage: float


class ComplexityMetric(BaseModel):
    file_path: str
    function_name: Optional[str] = None
    cyclomatic_complexity: int
    cognitive_complexity: Optional[int] = None


class DependencyHealth(BaseModel):
    total_dependencies: int
    internal_dependencies: int
    external_dependencies: int
    circular_dependencies: int
    circular_dependency_groups: Optional[List[List[str]]] = None


class AnalyticsDashboard(BaseModel):
    repository_id: str
    total_files: int
    total_loc: int
    languages: List[LanguageBreakdown] = []
    avg_complexity: float = 0.0
    max_complexity: int = 0
    complexity_details: List[ComplexityMetric] = []
    dependency_health: Optional[DependencyHealth] = None
    issue_counts: dict = {}  # {severity: count}
    recent_analyses: List[ReviewReportResponse] = []


# ──────────────────────────────────────────────
# Job Schemas
# ──────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Generic
# ──────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: List = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
