"""RAG Chat API endpoints."""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion, SourceFile
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.schemas import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    Citation,
)
from app.core.security import get_current_user
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService

router = APIRouter()


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new RAG chat session bound to a repository."""
    # Check repository ownership
    r_stmt = select(Repository).where(
        Repository.id == payload.repository_id,
        Repository.owner_id == current_user.id,
    )
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    session = ChatSession(
        user_id=current_user.id,
        repository_id=payload.repository_id,
        title=payload.title or f"Chat on {repo.name}",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    repository_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's active chat sessions."""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatSession.is_active == True)
        .order_by(desc(ChatSession.updated_at))
    )
    if repository_id:
        stmt = stmt.where(ChatSession.repository_id == repository_id)

    sessions = (await db.execute(stmt)).scalars().all()
    return sessions


@router.get("/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve chat session details."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await db.delete(session)
    await db.commit()
    return None


@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get message history for a session."""
    s_stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session = (await db.execute(s_stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    m_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = (await db.execute(m_stmt)).scalars().all()

    response = []
    for m in messages:
        cits = []
        if m.citations_json:
            try:
                raw_cits = json.loads(m.citations_json)
                cits = [Citation(**c) for c in raw_cits]
            except Exception:
                pass

        response.append(
            ChatMessageResponse(
                id=m.id,
                role=m.role.value if hasattr(m.role, "value") else str(m.role),
                content=m.content,
                citations=cits,
                model_used=m.model_used,
                latency_ms=m.latency_ms,
                created_at=m.created_at,
            )
        )
    return response


@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send user message, execute RAG hybrid search against repository, and return AI synthesis."""
    # 1. Verify session
    s_stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session = (await db.execute(s_stmt)).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Fetch repository
    r_stmt = select(Repository).where(Repository.id == session.repository_id)
    repo = (await db.execute(r_stmt)).scalars().first()

    # 2. Record User Message
    user_msg = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=payload.content,
    )
    db.add(user_msg)
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    await db.flush()

    # 3. Find current repository version
    v_stmt = select(RepositoryVersion.id).where(
        RepositoryVersion.repository_id == session.repository_id,
        RepositoryVersion.is_current == True,
    )
    version_id = (await db.execute(v_stmt)).scalars().first()
    if not version_id:
        v_stmt2 = select(RepositoryVersion.id).where(
            RepositoryVersion.repository_id == session.repository_id
        ).order_by(desc(RepositoryVersion.created_at)).limit(1)
        version_id = (await db.execute(v_stmt2)).scalars().first()

    retrieved_chunks = []
    repo_overview = f"Repository: {repo.name if repo else 'Project'} ({repo.primary_language or 'code' if repo else 'code'})\n"
    if repo and repo.description:
        repo_overview += f"Description: {repo.description}\n"

    if version_id:
        # Build file inventory overview
        sf_stmt = (
            select(SourceFile.file_path, SourceFile.loc)
            .where(SourceFile.version_id == version_id)
            .order_by(desc(SourceFile.loc))
            .limit(15)
        )
        source_files = (await db.execute(sf_stmt)).all()
        if source_files:
            files_str = ", ".join([f"{f[0]} ({f[1]} lines)" for f in source_files])
            repo_overview += f"Key Files in Repository: {files_str}\n"

        # Check for README
        readme_stmt = select(SourceFile.content).where(
            SourceFile.version_id == version_id,
            SourceFile.file_path.ilike("%readme%"),
        ).limit(1)
        readme_content = (await db.execute(readme_stmt)).scalars().first()
        if readme_content:
            repo_overview += f"README Excerpt:\n{readme_content[:1000]}\n"

        retrieved_chunks = await RAGService.hybrid_search(
            query=payload.content,
            version_id=version_id,
            db=db,
            top_k=8,
        )

        # Fallback to source files if no chunks found
        if not retrieved_chunks:
            search_terms = [w.strip() for w in payload.content.split() if len(w) > 3][:3]
            conds = [SourceFile.content.ilike(f"%{t}%") for t in search_terms]
            if conds:
                sf_fb = select(SourceFile).where(SourceFile.version_id == version_id, or_(*conds)).limit(3)
                fb_files = (await db.execute(sf_fb)).scalars().all()
                for fb in fb_files:
                    retrieved_chunks.append({
                        "chunk_id": fb.id,
                        "file_path": fb.file_path,
                        "name": fb.file_name,
                        "start_line": 1,
                        "end_line": min(50, fb.loc or 50),
                        "language": fb.language,
                        "content": (fb.content or "")[:1200],
                        "score": 0.8,
                    })

    # Fetch recent conversation history for multi-turn coherence
    h_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.id != user_msg.id)
        .order_by(desc(ChatMessage.created_at))
        .limit(6)
    )
    prev_messages = list(reversed((await db.execute(h_stmt)).scalars().all()))
    chat_history = [
        {
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            "content": m.content[:1000],
        }
        for m in prev_messages
    ]

    # 4. Synthesize with LLM & validate citations
    llm_result = await LLMService.generate_response(
        user_query=payload.content,
        retrieved_chunks=retrieved_chunks,
        chat_history=chat_history,
        repo_overview=repo_overview,
    )

    # 5. Record Assistant Message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=llm_result["content"],
        citations_json=json.dumps(llm_result["citations"]),
        model_used=llm_result["model_used"],
        latency_ms=llm_result["latency_ms"],
    )
    db.add(assistant_msg)
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(assistant_msg)

    cits = [Citation(**c) for c in llm_result["citations"]]
    return ChatMessageResponse(
        id=assistant_msg.id,
        role=assistant_msg.role.value if hasattr(assistant_msg.role, "value") else str(assistant_msg.role),
        content=assistant_msg.content,
        citations=cits,
        model_used=assistant_msg.model_used,
        latency_ms=assistant_msg.latency_ms,
        created_at=assistant_msg.created_at,
    )
