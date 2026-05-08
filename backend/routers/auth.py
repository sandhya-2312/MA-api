from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import User
from backend.schemas import ChangePasswordRequest, LoginRequest, TokenResponse
from backend.utils.auth import create_access_token, get_current_user
from backend.utils.password import hash_password, verify_password

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Login API: validates credentials and returns JWT token.
    # Case-insensitive username match (prevents Viewer1 vs viewer1 login failures).
    user = db.query(User).filter(func.lower(User.username) == payload.username.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        first_login=user.first_login,
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
