"""Generated documentation model."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class DocType(str, enum.Enum):
    README = "readme"
    ARCHITECTURE = "architecture"
    API_SPEC = "api_spec"
    DB_SCHEMA = "db_schema"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    COMPONENT_DOC = "component_doc"
    FULL_DOCS = "full_docs"


class GeneratedDoc(Base):
    __tablename__ = "generated_docs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("repository_versions.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(SAEnum(DocType), nullable=False)
    title = Column(String(500), nullable=False)
    content_markdown = Column(Text(length=16_777_215), nullable=False)  # MEDIUMTEXT
    content_html = Column(Text(length=16_777_215), nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON with generation details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="generated_docs")

    __table_args__ = (
        Index("idx_doc_repo", "repository_id"),
        Index("idx_doc_version", "version_id"),
        Index("idx_doc_type", "doc_type"),
    )
