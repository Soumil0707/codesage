"""Repository, RepositoryVersion, SourceFile models."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BigInteger,
    ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class RepositorySource(str, enum.Enum):
    GITHUB = "github"
    ZIP_UPLOAD = "zip_upload"


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(SAEnum(RepositorySource), nullable=False)
    github_url = Column(String(500), nullable=True)
    default_branch = Column(String(100), default="main", nullable=True)
    is_private = Column(Boolean, default=False, nullable=False)
    primary_language = Column(String(50), nullable=True)
    total_files = Column(Integer, default=0, nullable=False)
    total_loc = Column(Integer, default=0, nullable=False)
    indexing_status = Column(SAEnum(IndexingStatus), default=IndexingStatus.PENDING, nullable=False)
    last_indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="repositories")
    versions = relationship("RepositoryVersion", back_populates="repository", cascade="all, delete-orphan")
    analysis_reports = relationship("AnalysisReport", back_populates="repository", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="repository", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="repository", cascade="all, delete-orphan")
    generated_docs = relationship("GeneratedDoc", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_repo_owner", "owner_id"),
        Index("idx_repo_status", "indexing_status"),
    )


class RepositoryVersion(Base):
    __tablename__ = "repository_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    commit_sha = Column(String(40), nullable=True)
    upload_hash = Column(String(64), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)
    file_count = Column(Integer, default=0, nullable=False)
    total_loc = Column(Integer, default=0, nullable=False)
    language_stats = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="versions")
    source_files = relationship("SourceFile", back_populates="version", cascade="all, delete-orphan")
    code_chunks = relationship("CodeChunk", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_version_repo", "repository_id"),
        Index("idx_version_current", "repository_id", "is_current"),
    )


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    language = Column(String(50), nullable=False)
    content = Column(Text(length=16_777_215), nullable=True)  # MEDIUMTEXT
    content_hash = Column(String(64), nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    loc = Column(Integer, default=0, nullable=False)
    is_parseable = Column(Boolean, default=True, nullable=False)
    parse_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    version = relationship("RepositoryVersion", back_populates="source_files")

    __table_args__ = (
        Index("idx_file_version", "version_id"),
        Index("idx_file_path", "version_id", "file_path"),
        Index("idx_file_language", "language"),
    )
