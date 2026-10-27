"""Auth API routes."""
import logging
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_password, create_access_token, create_refresh_token, hash_password
from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.schemas import (
    LoginRequest, TokenResponse, UserOut, UserCreate,
    AuthConfigResponse, GoogleAuthRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config():
    """Public discovery endpoint for enabled authentication methods."""
    return AuthConfigResponse(
        google_enabled=bool(settings.GOOGLE_OAUTH_ENABLED and settings.GOOGLE_CLIENT_ID),
        google_client_id=settings.GOOGLE_CLIENT_ID if settings.GOOGLE_OAUTH_ENABLED else None,
        environment=settings.ENVIRONMENT,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        role=user.role.value,
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate or register a citizen using verified Google OAuth ID Token."""
    if not settings.GOOGLE_OAUTH_ENABLED or not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google sign-in is not configured on this server. Please use email/password sign in.",
        )

    # Validate ID Token with Google tokeninfo endpoint
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": body.credential},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Google identity token",
                )
            token_info = resp.json()
    except httpx.RequestError as exc:
        logger.error(f"Google token verification request failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not communicate with Google verification service",
        )

    # Verify audience, issuer, email_verified
    aud = token_info.get("aud")
    if aud != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token audience does not match this application",
        )

    iss = token_info.get("iss", "")
    if iss not in ["accounts.google.com", "https://accounts.google.com"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Untrusted Google token issuer",
        )

    email_verified = token_info.get("email_verified")
    if not (email_verified is True or email_verified == "true"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified",
        )

    # Expiry verification
    import time
    exp = token_info.get("exp")
    if exp:
        try:
            if int(exp) < int(time.time()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token has expired",
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token expiry claim",
            )

    google_sub = token_info.get("sub")
    email = token_info.get("email", "").lower().strip()
    full_name = token_info.get("name") or email.split("@")[0]

    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete identity claims from Google",
        )

    # 1. Match by google_id
    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()
    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            role=user.role.value,
        )

    # 2. Check if account with email exists (account linking verification)
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        if not body.link_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Enter your password to link your Google account.",
            )
        if not body.password_for_linking or not verify_password(body.password_for_linking, existing.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for linking account.",
            )
        existing.google_id = google_sub
        await db.commit()
        return TokenResponse(
            access_token=create_access_token(existing.id),
            refresh_token=create_refresh_token(existing.id),
            role=existing.role.value,
        )

    # 3. Create new citizen account
    new_user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        google_id=google_sub,
        role=UserRole.CITIZEN,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return TokenResponse(
        access_token=create_access_token(new_user.id),
        refresh_token=create_refresh_token(new_user.id),
        role=new_user.role.value,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Self-registration for citizens only."""
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=UserRole.CITIZEN,
    )
    db.add(user)
    await db.flush()
    return user
