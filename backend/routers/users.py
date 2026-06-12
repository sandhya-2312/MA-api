from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.enums import UserRole
from backend.models import Project, User, UserProject
from backend.schemas import (
    ProfileUpdateRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserResponse,
    UserUpdateRequest,
)
from backend.utils.auth import create_access_token, get_current_user, require_roles
from backend.utils.password import hash_password

router = APIRouter(tags=["Users"])


def _normalize_email(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip().lower()


def build_user_response(user: User, access_token: str | None = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        first_login=user.first_login,
        assigned_project_ids=[assignment.project_id for assignment in user.projects],
        contact_no=user.contact_no,
        full_name=user.full_name,
        email=user.email,
        designation=user.designation,
        access_token=access_token,
    )


def _ensure_email_available(db: Session, email: str | None, exclude_user_id: int | None) -> None:
    if not email:
        return
    q = db.query(User).filter(User.email == email)
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    if q.first():
        raise HTTPException(status_code=409, detail="Email already in use")


def _require_manageable_user(target: User | None, current_admin: User) -> User:
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admins can only manage Member/Viewer accounts")
    if target.created_by_admin_id != current_admin.id:
        raise HTTPException(status_code=403, detail="You can only manage users you created")
    return target


@router.post("/users", response_model=UserCreateResponse)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("Admin")),
):
    # Admin API: creates user with admin-provided credentials.
    if payload.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Create separate admin accounts outside member management")
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    existing_user = (
        db.query(User).filter(func.lower(User.username) == username.lower()).first()
    )
    if existing_user:
        raise HTTPException(status_code=409, detail="Username already exists")

    normalized_email = _normalize_email(payload.email)
    _ensure_email_available(db, normalized_email, exclude_user_id=None)

    project_ids = list(dict.fromkeys(payload.project_ids))
    if project_ids:
        found_ids = {
            project.id
            for project in db.query(Project.id).filter(Project.id.in_(project_ids)).all()
        }
        missing_ids = [project_id for project_id in project_ids if project_id not in found_ids]
        if missing_ids:
            raise HTTPException(status_code=404, detail="One or more projects were not found")

    new_user = User(
        username=username,
        role=payload.role,
        password_hash=hash_password(payload.password),
        first_login=False,
        contact_no=payload.contact_no.strip() if payload.contact_no else None,
        full_name=(payload.full_name or "").strip() or None,
        email=normalized_email,
        designation=(payload.designation or "").strip() or None,
        created_by_admin_id=current_admin.id,
    )
    db.add(new_user)
    db.flush()

    for project_id in project_ids:
        db.add(UserProject(user_id=new_user.id, project_id=project_id))

    db.commit()
    db.refresh(new_user)

    return UserCreateResponse(user=build_user_response(new_user), temporary_password=None)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("Admin")),
):
    # Admin API: lists only Member/Viewer accounts created by current admin.
    users = (
        db.query(User)
        .filter(User.created_by_admin_id == current_admin.id, User.role != UserRole.ADMIN)
        .order_by(User.id.asc())
        .all()
    )
    return [build_user_response(user) for user in users]


@router.delete("/users/{id}")
def delete_user(
    id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("Admin")),
):
    # Admin API: deletes a managed Member/Viewer by id.
    user = _require_manageable_user(db.query(User).filter(User.id == id).first(), current_admin)
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.put("/users/{id}", response_model=UserResponse)
def update_user(
    id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("Admin")),
):
    # Admin API: edits managed Member/Viewer role, username, and project assignments.
    user = _require_manageable_user(db.query(User).filter(User.id == id).first(), current_admin)
    if payload.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Members page supports only Member/Viewer roles")

    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    duplicate_user = (
        db.query(User)
        .filter(func.lower(User.username) == username.lower(), User.id != id)
        .first()
    )
    if duplicate_user:
        raise HTTPException(status_code=409, detail="Username already exists")

    user.username = username
    user.role = payload.role
    update_fields = payload.model_dump(exclude_unset=True)
    if "contact_no" in update_fields:
        user.contact_no = (payload.contact_no or "").strip() or None
    if "full_name" in update_fields:
        user.full_name = (payload.full_name or "").strip() or None
    if "email" in update_fields:
        user.email = _normalize_email(payload.email)
        _ensure_email_available(db, user.email, exclude_user_id=id)
    if "designation" in update_fields:
        user.designation = (payload.designation or "").strip() or None

    db.query(UserProject).filter(UserProject.user_id == id).delete()
    if payload.role != UserRole.ADMIN:
        for project_id in payload.project_ids:
            db.add(UserProject(user_id=id, project_id=project_id))

    db.commit()
    db.refresh(user)
    return build_user_response(user)


@router.get("/profile", response_model=UserResponse)
def read_profile(
    current_user: User = Depends(get_current_user),
):
    return build_user_response(current_user)


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Profile API: updates current user's profile and optional password.
    original_username = current_user.username
    duplicate_user = (
        db.query(User)
        .filter(User.username == payload.username, User.id != current_user.id)
        .first()
    )
    if duplicate_user:
        raise HTTPException(status_code=409, detail="Username already exists")

    current_user.username = payload.username
    update_fields = payload.model_dump(exclude_unset=True)
    if "contact_no" in update_fields:
        current_user.contact_no = payload.contact_no.strip() if payload.contact_no else None
    if "full_name" in update_fields:
        current_user.full_name = (payload.full_name or "").strip() or None
    if "email" in update_fields:
        current_user.email = _normalize_email(payload.email)
        _ensure_email_available(db, current_user.email, exclude_user_id=current_user.id)
    if "designation" in update_fields:
        current_user.designation = (payload.designation or "").strip() or None

    password_changed = False
    if payload.new_password:
        current_user.password_hash = hash_password(payload.new_password)
        current_user.first_login = False
        password_changed = True

    db.commit()
    db.refresh(current_user)

    access_token = None
    if password_changed or current_user.username != original_username:
        access_token = create_access_token({"sub": current_user.username, "role": current_user.role})

    return build_user_response(current_user, access_token=access_token)
