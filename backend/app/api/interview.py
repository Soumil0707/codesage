"""Interview Intelligence API endpoints."""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.interview import InterviewSession, InterviewQuestion, InterviewAnswer
from app.schemas import (
    InterviewStart,
    InterviewSessionResponse,
    InterviewQuestionResponse,
    InterviewAnswerSubmit,
    InterviewAnswerResponse,
    InterviewReportResponse,
)
from app.core.security import get_current_user
from app.services.interview_service import InterviewService

router = APIRouter()


@router.post("", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_interview(
    payload: InterviewStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new codebase-grounded technical interview session."""
    r_stmt = select(Repository).where(
        Repository.id == payload.repository_id,
        Repository.owner_id == current_user.id,
    )
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    session = await InterviewService.start_session(
        user_id=current_user.id,
        repository_id=payload.repository_id,
        title=payload.title or f"Technical Interview: {repo.name}",
        difficulty=payload.difficulty,
        db=db,
    )
    return session


@router.get("", response_model=List[InterviewSessionResponse])
async def list_interviews(
    repository_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List technical interview sessions."""
    stmt = (
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(desc(InterviewSession.created_at))
    )
    if repository_id:
        stmt = stmt.where(InterviewSession.repository_id == repository_id)

    sessions = (await db.execute(stmt)).scalars().all()
    return sessions


@router.get("/{session_id}", response_model=InterviewSessionResponse)
async def get_interview_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get interview session details."""
    stmt = select(InterviewSession).where(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@router.post("/{session_id}/next", response_model=InterviewQuestionResponse)
async def get_next_question(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advance to and generate next interview question grounded in the repository."""
    stmt = select(InterviewSession).where(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    q = await InterviewService.generate_next_question(session_id, db)
    if not q:
        raise HTTPException(status_code=400, detail="Cannot generate more questions for this session")

    return InterviewQuestionResponse(
        id=q.id,
        question_number=q.question_number,
        difficulty=q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty),
        category=q.category.value if hasattr(q.category, "value") else str(q.category),
        question_text=q.question_text,
        context_code=q.context_code,
        context_file_path=q.context_file_path,
        is_follow_up=q.is_follow_up,
        answer=None,
    )


@router.post("/{session_id}/questions/{question_id}/answer", response_model=InterviewAnswerResponse)
async def submit_answer(
    session_id: str,
    question_id: str,
    payload: InterviewAnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit candidate response to question and receive rubric evaluation."""
    s_stmt = select(InterviewSession).where(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    )
    session = (await db.execute(s_stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    try:
        answer = await InterviewService.evaluate_answer(question_id, payload.answer_text, db)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    eval_dict = json.loads(answer.evaluation_json) if answer.evaluation_json else {}
    demo_topics = json.loads(answer.topics_demonstrated_json) if answer.topics_demonstrated_json else []
    missed_topics = json.loads(answer.topics_missed_json) if answer.topics_missed_json else []

    return InterviewAnswerResponse(
        id=answer.id,
        score=answer.score,
        max_score=answer.max_score,
        answer_text=answer.answer_text,
        evaluation=eval_dict,
        topics_demonstrated=demo_topics,
        topics_missed=missed_topics,
    )


@router.post("/{session_id}/complete", response_model=InterviewReportResponse)
async def complete_interview(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete interview session and compile comprehensive evaluation report."""
    stmt = select(InterviewSession).where(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    final_report = await InterviewService.complete_session(session_id, db)
    return await get_interview_report(session_id, current_user, db)


@router.get("/{session_id}/report", response_model=InterviewReportResponse)
async def get_interview_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full scorecard, strengths, weaknesses, and revision guides."""
    stmt = (
        select(InterviewSession)
        .where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
        .options(selectinload(InterviewSession.questions).selectinload(InterviewQuestion.answer))
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    rep_dict = json.loads(session.final_report_json) if session.final_report_json else {}
    topics = json.loads(session.topics_covered_json) if session.topics_covered_json else []
    strengths = json.loads(session.strengths_json) if session.strengths_json else []
    weaknesses = json.loads(session.weaknesses_json) if session.weaknesses_json else []

    q_responses = []
    for q in session.questions:
        ans_resp = None
        if q.answer:
            eval_dict = json.loads(q.answer.evaluation_json) if q.answer.evaluation_json else {}
            demo_topics = json.loads(q.answer.topics_demonstrated_json) if q.answer.topics_demonstrated_json else []
            missed_topics = json.loads(q.answer.topics_missed_json) if q.answer.topics_missed_json else []
            ans_resp = InterviewAnswerResponse(
                id=q.answer.id,
                score=q.answer.score,
                max_score=q.answer.max_score,
                answer_text=q.answer.answer_text,
                evaluation=eval_dict,
                topics_demonstrated=demo_topics,
                topics_missed=missed_topics,
            )

        q_responses.append(
            InterviewQuestionResponse(
                id=q.id,
                question_number=q.question_number,
                difficulty=q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty),
                category=q.category.value if hasattr(q.category, "value") else str(q.category),
                question_text=q.question_text,
                context_code=q.context_code,
                context_file_path=q.context_file_path,
                is_follow_up=q.is_follow_up,
                answer=ans_resp,
            )
        )

    return InterviewReportResponse(
        id=session.id,
        title=session.title,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        current_difficulty=session.current_difficulty.value if hasattr(session.current_difficulty, "value") else str(session.current_difficulty),
        total_questions=session.total_questions,
        total_score=session.total_score,
        max_score=session.max_score,
        started_at=session.started_at,
        completed_at=session.completed_at,
        created_at=session.created_at,
        topics_covered=topics,
        strengths=strengths,
        weaknesses=weaknesses,
        final_report=rep_dict,
        questions=q_responses,
    )
