"""Documentation Generation API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion
from app.models.docs import GeneratedDoc, DocType
from app.schemas import DocGenerateRequest, DocResponse
from app.core.security import get_current_user
from app.services.docs_service import DocsService

router = APIRouter()


@router.post("/generate", response_model=DocResponse, status_code=status.HTTP_201_CREATED)
async def generate_document(
    payload: DocGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate architecture documentation, README, or API specs."""
    r_stmt = select(Repository).where(
        Repository.id == payload.repository_id,
        Repository.owner_id == current_user.id,
    )
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    version_id = payload.version_id
    if not version_id:
        v_stmt = select(RepositoryVersion.id).where(
            RepositoryVersion.repository_id == payload.repository_id,
            RepositoryVersion.is_current == True,
        )
        version_id = (await db.execute(v_stmt)).scalars().first()
        if not version_id:
            raise HTTPException(status_code=400, detail="Repository has no indexed versions")

    doc_type = DocType(payload.doc_type)
    doc = await DocsService.generate_documentation(
        repository_id=payload.repository_id,
        version_id=version_id,
        doc_type=doc_type,
        db=db,
    )
    return doc


@router.get("/{repo_id}", response_model=List[DocResponse])
async def list_documents(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List generated documentation files for a repository."""
    r_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    stmt = (
        select(GeneratedDoc)
        .where(GeneratedDoc.repository_id == repo_id)
        .order_by(desc(GeneratedDoc.created_at))
    )
    docs = (await db.execute(stmt)).scalars().all()
    return docs


@router.get("/{repo_id}/{doc_id}", response_model=DocResponse)
async def get_document(
    repo_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve specific generated document."""
    stmt = (
        select(GeneratedDoc)
        .join(Repository)
        .where(
            GeneratedDoc.id == doc_id,
            GeneratedDoc.repository_id == repo_id,
            Repository.owner_id == current_user.id,
        )
    )
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{repo_id}/{doc_id}/export")
async def export_document(
    repo_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export document as raw Markdown attachment download."""
    stmt = (
        select(GeneratedDoc)
        .join(Repository)
        .where(
            GeneratedDoc.id == doc_id,
            GeneratedDoc.repository_id == repo_id,
            Repository.owner_id == current_user.id,
        )
    )
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = f"{doc.doc_type.value}_{repo_id[:8]}.md"
    return Response(
        content=doc.content_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
