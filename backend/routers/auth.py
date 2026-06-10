import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    TokenResponse,
)
from backend.utils.auth import create_access_token, get_current_user
from backend.utils.password import generate_random_password, hash_password, verify_password

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)
REMEMBER_ME_EXPIRE_DAYS = int(os.getenv("REMEMBER_ME_EXPIRE_DAYS", "30"))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Login API: validates credentials and returns JWT token.
    # Case-insensitive username match (prevents Viewer1 vs viewer1 login failures).
    username = payload.username.strip()
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user:
        logger.warning("Login rejected for unknown username %s.", username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(payload.password, user.password_hash):
        logger.warning("Login rejected for user %s due to invalid password.", user.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expires_delta = (
        timedelta(days=REMEMBER_ME_EXPIRE_DAYS) if payload.remember_me else None
    )
    token = create_access_token({"sub": user.username, "role": user.role}, expires_delta=expires_delta)
    logger.info(
        "Login accepted for user %s (first_login=%s, remember_me=%s).",
        user.username,
        user.first_login,
        payload.remember_me,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        first_login=user.first_login,
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not username or not email:
        raise HTTPException(status_code=400, detail="Username and email are required")

    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user or not user.email or user.email.lower() != email:
        raise HTTPException(
            status_code=400,
            detail="Username and email do not match. Verify your details or contact your administrator.",
        )

    temporary_password = generate_random_password()
    user.password_hash = hash_password(temporary_password)
    user.first_login = True
    db.commit()

    logger.info("Password reset via forgot-password for user %s.", user.username)
    return ForgotPasswordResponse(
        message="Password reset successful. Sign in with the temporary password below, then update your credentials.",
        temporary_password=temporary_password,
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Change password API: mandatory for first login and updates stored hash.
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.first_login = False
    db.commit()
    return {"message": "Password changed successfully"}
