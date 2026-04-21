"""
Authentication routes — JWT + bcrypt.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.course import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str


class UserOut(BaseModel):
    username: str
    full_name: str
    role: str
    created_at: str | None = None


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # First registered user becomes admin; rest are regular users.
    user_count = await db.scalar(select(func.count()).select_from(User)) or 0
    role = "admin" if user_count == 0 else "user"

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name or req.username,
        role=role,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.username, role=user.role)
    return TokenResponse(
        access_token=token,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.username, role=user.role or "user")
    return TokenResponse(
        access_token=token,
        username=user.username,
        full_name=user.full_name,
        role=user.role or "user",
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        username=user.username,
        full_name=user.full_name or user.username,
        role=user.role or "user",
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
