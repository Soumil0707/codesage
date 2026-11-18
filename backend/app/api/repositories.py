"""Repositories API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion, SourceFile, RepositorySource, IndexingStatus
from app.models.jobs import IndexingJob
from app.schemas import (
    RepoCreateGitHub,
    RepoResponse,
    RepoDetailResponse,
    VersionResponse,
    FileResponse,
    JobStatusResponse,
)
from app.core.security import get_current_user
from app.services.ingestion import IngestionService
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/github", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def import_github_repository(
    payload: RepoCreateGitHub,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import repository from GitHub URL."""
    # Derive name if not provided
    name = payload.name
    if not name:
        parts = payload.github_url.rstrip("/").split("/")
        name = parts[-1]
        if name.endswith(".git"):
            name = name[:-4]

    repo = Repository(
        owner_id=current_user.id,
        name=name,
        source=RepositorySource.GITHUB,
        github_url=payload.github_url,
        default_branch=payload.branch or "main",
        indexing_status=IndexingStatus.PENDING,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    # Ingest repository files asynchronously via IngestionService
    try:
        await IngestionService.ingest_github(
            repository_id=repo.id,
            github_url=payload.github_url,
            branch=payload.branch or "main",
            token=payload.github_token,
            db=db,
        )
        await db.refresh(repo)
    except Exception as e:
        # Ingestion failure recorded in status
        pass

    return repo


@router.post("/upload", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def upload_repository_zip(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Safely upload and ingest repository as a ZIP archive."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    content = await file.read()
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum upload size of {settings.UPLOAD_MAX_SIZE_MB}MB",
        )

    repo = Repository(
        owner_id=current_user.id,
        name=name,
        description=description,
        source=RepositorySource.ZIP_UPLOAD,
        indexing_status=IndexingStatus.PENDING,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    try:
        await IngestionService.ingest_zip(
            repository_id=repo.id,
            zip_bytes=content,
            upload_filename=file.filename,
            db=db,
        )
        await db.refresh(repo)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process archive: {str(e)}")

    return repo


@router.get("", response_model=List[RepoResponse])
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all repositories owned by the current user."""
    stmt = (
        select(Repository)
        .where(Repository.owner_id == current_user.id)
        .order_by(desc(Repository.created_at))
    )
    results = (await db.execute(stmt)).scalars().all()
    return results


@router.get("/{repo_id}", response_model=RepoDetailResponse)
async def get_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get repository details along with all indexed versions."""
    stmt = (
        select(Repository)
        .where(Repository.id == repo_id, Repository.owner_id == current_user.id)
        .options(selectinload(Repository.versions))
    )
    repo = (await db.execute(stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository and all associated indexed data."""
    stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    await db.delete(repo)
    await db.commit()
    return None


@router.get("/{repo_id}/files", response_model=List[FileResponse])
async def list_repository_files(
    repo_id: str,
    version_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List source files for the repository's current or specified version."""
    # Verify ownership
    repo_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(repo_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Determine target version
    if not version_id:
        v_stmt = select(RepositoryVersion.id).where(
            RepositoryVersion.repository_id == repo_id,
            RepositoryVersion.is_current == True,
        )
        version_id = (await db.execute(v_stmt)).scalars().first()
        if not version_id:
            return []

    stmt = select(SourceFile).where(SourceFile.version_id == version_id)
    if language:
        stmt = stmt.where(SourceFile.language == language)
    stmt = stmt.order_by(SourceFile.file_path)

    files = (await db.execute(stmt)).scalars().all()
    return files


@router.get("/{repo_id}/files/{file_id}", response_model=FileResponse)
async def get_repository_file(
    repo_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve content and metadata for a specific source file."""
    repo_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(repo_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    stmt = select(SourceFile).join(RepositoryVersion).where(
        SourceFile.id == file_id,
        RepositoryVersion.repository_id == repo_id,
    )
    file_record = (await db.execute(stmt)).scalars().first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    return file_record


@router.get("/{repo_id}/jobs", response_model=List[JobStatusResponse])
async def get_indexing_jobs(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of indexing jobs for this repository."""
    repo_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(repo_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    stmt = (
        select(IndexingJob)
        .where(IndexingJob.repository_id == repo_id)
        .order_by(desc(IndexingJob.created_at))
    )
    jobs = (await db.execute(stmt)).scalars().all()
    return jobs


@router.post("/{repo_id}/reindex", status_code=status.HTTP_200_OK)
async def reindex_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger or restart codebase indexing pipeline."""
    from datetime import datetime
    from app.models.jobs import JobStatus, JobType
    repo_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(repo_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    v_stmt = select(RepositoryVersion).where(
        RepositoryVersion.repository_id == repo_id,
        RepositoryVersion.is_current == True,
    )
    version = (await db.execute(v_stmt)).scalars().first()
    if not version:
        raise HTTPException(status_code=400, detail="Repository has no versions")

    j_stmt = select(IndexingJob).where(
        IndexingJob.repository_id == repo_id,
        IndexingJob.version_id == version.id,
    )
    job = (await db.execute(j_stmt)).scalars().first()
    if job:
        job.status = JobStatus.PENDING
        job.retry_count = 0
        job.error_message = None
        job.worker_id = None
    else:
        job = IndexingJob(
            repository_id=repo_id,
            version_id=version.id,
            job_type=JobType.FILE_PARSING,
            status=JobStatus.PENDING,
            priority=10,
            idempotency_key=f"parse_{version.id}_{int(datetime.utcnow().timestamp())}",
        )
        db.add(job)

    repo.indexing_status = IndexingStatus.PENDING
    await db.commit()
    return {"status": "indexing_scheduled", "job_id": job.id}
