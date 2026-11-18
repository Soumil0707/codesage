"""Developer Analytics API endpoints."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion
from app.schemas import AnalyticsDashboard
from app.core.security import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.dependency_service import DependencyService

router = APIRouter()


@router.get("/{repo_id}/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full analytics dashboard with measured metrics and dependency health."""
    r_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    data = await AnalyticsService.get_dashboard(repo_id, db)
    return data


@router.get("/{repo_id}/graph")
async def get_dependency_graph(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve React Flow formatted dependency graph with circular dependency analysis."""
    r_stmt = select(Repository).where(Repository.id == repo_id, Repository.owner_id == current_user.id)
    repo = (await db.execute(r_stmt)).scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    v_stmt = select(RepositoryVersion.id).where(
        RepositoryVersion.repository_id == repo_id,
        RepositoryVersion.is_current == True,
    )
    version_id = (await db.execute(v_stmt)).scalars().first()
    if not version_id:
        return {"nodes": [], "edges": [], "circular_dependencies": []}

    graph = await DependencyService.get_react_flow_graph(version_id, db)
    return graph
