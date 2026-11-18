"""Interview models: InterviewSession, InterviewQuestion, InterviewAnswer."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, Integer, Float, Boolean,
    ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class InterviewStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(InterviewStatus), default=InterviewStatus.IN_PROGRESS, nullable=False)
    current_difficulty = Column(SAEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, nullable=False)
    total_questions = Column(Integer, default=0, nullable=False)
    total_score = Column(Float, default=0.0, nullable=False)
    max_score = Column(Float, default=0.0, nullable=False)
    topics_covered_json = Column(Text, nullable=True)  # JSON array
    strengths_json = Column(Text, nullable=True)  # JSON array
    weaknesses_json = Column(Text, nullable=True)  # JSON array
    final_report_json = Column(Text, nullable=True)  # JSON object with full report
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    repository = relationship("Repository", back_populates="interview_sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan",
                             order_by="InterviewQuestion.question_number")

    __table_args__ = (
        Index("idx_interview_user", "user_id"),
        Index("idx_interview_repo", "repository_id"),
        Index("idx_interview_status", "status"),
    )


class QuestionCategory(str, enum.Enum):
    ARCHITECTURE = "architecture"
    DESIGN_PATTERNS = "design_patterns"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE = "performance"
    SECURITY = "security"
    TESTING = "testing"
    DATABASE = "database"
    ALGORITHMS = "algorithms"
    CODE_QUALITY = "code_quality"
    EDGE_CASES = "edge_cases"


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    difficulty = Column(SAEnum(DifficultyLevel), nullable=False)
    category = Column(SAEnum(QuestionCategory), nullable=False)
    question_text = Column(Text, nullable=False)
    context_code = Column(Text, nullable=True)  # Relevant code snippet from repo
    context_file_path = Column(String(500), nullable=True)
    expected_topics_json = Column(Text, nullable=True)  # JSON array of expected answer topics
    is_follow_up = Column(Boolean, default=False, nullable=False)
    parent_question_id = Column(String(36), ForeignKey("interview_questions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_question_session", "session_id"),
        Index("idx_question_difficulty", "difficulty"),
    )


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False)
    answer_text = Column(Text, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    max_score = Column(Float, default=10.0, nullable=False)
    evaluation_json = Column(Text, nullable=True)  # JSON: {correctness, depth, repo_understanding, feedback}
    topics_demonstrated_json = Column(Text, nullable=True)  # JSON array
    topics_missed_json = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    question = relationship("InterviewQuestion", back_populates="answer")

    __table_args__ = (
        Index("idx_answer_question", "question_id"),
    )
