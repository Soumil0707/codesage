"""Indexing job queue model (MySQL-backed task queue)."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, Integer, Float,
    ForeignKey, Index, Enum as SAEnum,
)
from app.database import Base
import enum


class JobType(str, enum.Enum):
    REPO_INGESTION = "repo_ingestion"
    FILE_PARSING = "file_parsing"
    EMBEDDING_GENERATION = "embedding_generation"
    CODE_ANALYSIS = "code_analysis"
    DOC_GENERATION = "doc_generation"
    DEPENDENCY_ANALYSIS = "dependency_analysis"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=True)
    job_type = Column(SAEnum(JobType), nullable=False)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # Higher = more priority
    payload_json = Column(Text, nullable=True)  # JSON with job-specific params
    result_json = Column(Text, nullable=True)  # JSON with results/errors
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    worker_id = Column(String(100), nullable=True)  # Which worker picked this up
    idempotency_key = Column(String(255), unique=True, nullable=True)  # Prevent duplicate jobs
    timeout_seconds = Column(Integer, default=600, nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_job_status_priority", "status", "priority"),
        Index("idx_job_repo", "repository_id"),
        Index("idx_job_type", "job_type"),
        Index("idx_job_worker", "worker_id"),
        Index("idx_job_idempotency", "idempotency_key"),
        Index("idx_job_scheduled", "scheduled_at"),
    )
