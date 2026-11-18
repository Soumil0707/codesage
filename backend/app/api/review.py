"""Code Review API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion
from app.models.analysis import AnalysisReport, AnalysisFinding, ReportType, VerificationStatus
from app.schemas import (
    ReviewRequest,
    ReviewReportResponse,
    FindingResponse,
)
from app.core.security import get_current_user
from app.services.review_service import ReviewService

router = APIRouter()


@router.post("", response_model=ReviewReportResponse, status_code=status.HTTP_201_CREATED)
async def start_code_review(
    payload: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute static & AI code review on the repository."""
    # Check repository access
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

    report_type = ReportType(payload.review_type)
    report = await ReviewService.run_review(
        repository_id=payload.repository_id,
        version_id=version_id,
        report_type=report_type,
        file_paths=payload.file_paths,
        db=db,
    )

    # Reload with findings
    stmt = (
        select(AnalysisReport)
        .where(AnalysisReport.id == report.id)
        .options(selectinload(AnalysisReport.findings))
    )
    loaded = (await db.execute(stmt)).scalars().first()
    return loaded


@router.get("/reports", response_model=List[ReviewReportResponse])
async def list_reports(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List code review reports for a repository."""
    r_stmt = select(Repository).where(
        Repository.id == repository_id,
        Repository.owner_id == current_user.id,
    )
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    stmt = (
        select(AnalysisReport)
        .where(AnalysisReport.repository_id == repository_id)
        .options(selectinload(AnalysisReport.findings))
        .order_by(desc(AnalysisReport.created_at))
    )
    reports = (await db.execute(stmt)).scalars().all()
    return reports


@router.get("/{report_id}", response_model=ReviewReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed code review report with findings."""
    stmt = (
        select(AnalysisReport)
        .join(Repository)
        .where(
            AnalysisReport.id == report_id,
            Repository.owner_id == current_user.id,
        )
        .options(selectinload(AnalysisReport.findings))
    )
    report = (await db.execute(stmt)).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding_status(
    finding_id: str,
    status: str = Query(..., pattern="^(verified_defect|ai_recommendation|false_positive|acknowledged)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update finding verification status."""
    stmt = (
        select(AnalysisFinding)
        .join(AnalysisReport)
        .join(Repository)
        .where(
            AnalysisFinding.id == finding_id,
            Repository.owner_id == current_user.id,
        )
    )
    finding = (await db.execute(stmt)).scalars().first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.verification_status = VerificationStatus(status)
    await db.commit()
    await db.refresh(finding)
    return finding
