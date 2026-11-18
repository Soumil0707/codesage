"""Analysis models: CodeChunk, CodeEmbedding, Dependency, AnalysisReport, AnalysisFinding."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, Float,
    ForeignKey, Index, LargeBinary, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ChunkType(str, enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    BLOCK = "block"
    IMPORT = "import"


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    chunk_type = Column(SAEnum(ChunkType), nullable=False)
    name = Column(String(500), nullable=True)  # function/class name
    content = Column(Text(length=16_777_215), nullable=False)  # MEDIUMTEXT
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    language = Column(String(50), nullable=False)
    parent_name = Column(String(500), nullable=True)  # enclosing class/module
    signature = Column(Text, nullable=True)
    docstring = Column(Text, nullable=True)
    token_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    version = relationship("RepositoryVersion", back_populates="code_chunks")
    embedding = relationship("CodeEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chunk_version", "version_id"),
        Index("idx_chunk_file", "version_id", "file_path"),
        Index("idx_chunk_type", "chunk_type"),
        Index("idx_chunk_language", "language"),
    )


class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String(36), ForeignKey("code_chunks.id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding_vector = Column(LargeBinary(length=16_777_215), nullable=False)  # MEDIUMBLOB for binary embedding
    embedding_model = Column(String(100), nullable=False)
    dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    chunk = relationship("CodeChunk", back_populates="embedding")

    __table_args__ = (
        Index("idx_embedding_chunk", "chunk_id"),
        Index("idx_embedding_model", "embedding_model"),
    )


class DependencyType(str, enum.Enum):
    IMPORT = "import"
    INHERITANCE = "inheritance"
    FUNCTION_CALL = "function_call"
    TYPE_REFERENCE = "type_reference"


class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=False)
    source_file = Column(String(500), nullable=False)
    target_file = Column(String(500), nullable=True)
    source_name = Column(String(500), nullable=False)
    target_name = Column(String(500), nullable=False)
    dependency_type = Column(SAEnum(DependencyType), nullable=False)
    is_external = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_dep_version", "version_id"),
        Index("idx_dep_source", "version_id", "source_file"),
        Index("idx_dep_type", "dependency_type"),
    )


class ReportType(str, enum.Enum):
    CODE_REVIEW = "code_review"
    SECURITY_SCAN = "security_scan"
    QUALITY_ANALYSIS = "quality_analysis"
    FULL_ANALYSIS = "full_analysis"


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(SAEnum(ReportType), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    summary = Column(Text, nullable=True)
    total_issues = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)
    metrics_json = Column(Text, nullable=True)  # JSON: LOC, complexity, etc.
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="analysis_reports")
    findings = relationship("AnalysisFinding", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_report_repo", "repository_id"),
        Index("idx_report_version", "version_id"),
        Index("idx_report_type", "report_type"),
    )


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, enum.Enum):
    BUG = "bug"
    CODE_SMELL = "code_smell"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    BEST_PRACTICE = "best_practice"


class VerificationStatus(str, enum.Enum):
    VERIFIED_DEFECT = "verified_defect"
    AI_RECOMMENDATION = "ai_recommendation"
    FALSE_POSITIVE = "false_positive"
    ACKNOWLEDGED = "acknowledged"


class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("analysis_reports.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    severity = Column(SAEnum(Severity), nullable=False)
    category = Column(SAEnum(FindingCategory), nullable=False)
    rule_id = Column(String(100), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    suggested_fix = Column(Text, nullable=True)
    code_snippet = Column(Text, nullable=True)
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.AI_RECOMMENDATION, nullable=False)
    confidence = Column(Float, default=0.5, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    report = relationship("AnalysisReport", back_populates="findings")

    __table_args__ = (
        Index("idx_finding_report", "report_id"),
        Index("idx_finding_severity", "severity"),
        Index("idx_finding_file", "file_path"),
        Index("idx_finding_category", "category"),
    )
