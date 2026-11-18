"""Authentication & User Management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from app.database import get_db
from app.config import get_settings
from app.models.user import User, UserSettings
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    UserSettingsUpdate,
    UserSettingsResponse,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user, initialize settings, and return access/refresh tokens."""
    # Check email duplicate
    stmt = select(User).where((User.email == payload.email) | (User.username == payload.username))
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        if existing.email == payload.email:
            raise HTTPException(status_code=400, detail="Email is already registered")
        raise HTTPException(status_code=400, detail="Username is already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    user_settings = UserSettings(
        user_id=user.id,
        theme="dark",
        default_language="python",
        notifications_enabled=True,
        llm_model_preference="gpt-4o-mini",
    )
    db.add(user_settings)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password."""
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalars().first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token using valid refresh token."""
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = decoded.get("sub")
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get profile information for current authenticated user."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    full_name: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update profile information for current authenticated user."""
    if full_name is not None:
        current_user.full_name = full_name
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user settings."""
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    user_settings = (await db.execute(stmt)).scalars().first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        await db.commit()
        await db.refresh(user_settings)
    return user_settings


@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user customization settings."""
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    user_settings = (await db.execute(stmt)).scalars().first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)

    if payload.theme is not None:
        user_settings.theme = payload.theme
    if payload.default_language is not None:
        user_settings.default_language = payload.default_language
    if payload.notifications_enabled is not None:
        user_settings.notifications_enabled = payload.notifications_enabled
    if payload.llm_model_preference is not None:
        user_settings.llm_model_preference = payload.llm_model_preference

    await db.commit()
    await db.refresh(user_settings)
    return user_settings
