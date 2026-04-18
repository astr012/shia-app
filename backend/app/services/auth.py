# ============================================================
# SignAI_OS â€” Authentication Service
#
# Password hashing, JWT token creation, validation,
# password strength enforcement, and role-based authorization.
# Uses bcrypt directly (passlib has compatibility issues with bcrypt 5.x).
# ============================================================

import re
from datetime import datetime, timedelta, timezone
from typing import List

import jwt
import bcrypt
from fastapi import HTTPException, status

from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def validate_password_strength(password: str) -> List[str]:
    """
    Enforce password policy from settings.
    Returns list of violation messages; empty list = valid.
    """
    violations: List[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        violations.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters."
        )
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        violations.append("Password must contain at least one uppercase letter.")
    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        violations.append("Password must contain at least one digit.")

    return violations


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory for role-based authorization.

    Usage:
        @router.delete("/resource", dependencies=[Depends(require_role("admin"))])
        async def delete_resource(): ...
    """
    from app.routers.auth import get_current_user
    from fastapi import Depends

    async def _role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return Depends(_role_checker)

