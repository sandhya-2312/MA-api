import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import get_secret_key
from sqlalchemy import func

from backend.database import get_db
from backend.models.enums import UserRole
from backend.models import User
from backend.utils.roles import normalize_role, to_user_role

load_dotenv()

SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if "role" in to_encode:
        to_encode["role"] = normalize_role(to_encode["role"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user:
        raise credentials_exception

    normalized_role = to_user_role(user.role)
    if normalized_role and normalized_role != user.role:
        user.role = normalized_role
        db.commit()
        db.refresh(user)

    return user


def require_roles(*allowed_roles: str | UserRole, allow_first_login: bool = False):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        normalized_roles = {normalize_role(role) for role in allowed_roles}
        current_role = normalize_role(current_user.role)
        if current_role not in normalized_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        if current_user.first_login and not allow_first_login:
            raise HTTPException(status_code=403, detail="Password change required on first login")
        return current_user

    return role_checker
