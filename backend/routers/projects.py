import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.enums import UserRole
from backend.models import Project, ProjectData, User, UserProject
from backend.schemas import (
    AdminProjectAssignedUser,
    AdminProjectDetail,
    AdminProjectOverview,
    AdminProjectsPageResponse,
    AdminProjectsStatsResponse,
    AssignUserRequest,
    DashboardDataPoint,
    InitialProjectItem,
    ProjectCreateRequest,
    ProjectResponse,
)
from backend.utils.auth import require_roles

router = APIRouter(tags=["Projects"])

def _norm_material_key(raw: object) -> str | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "") or "").strip().lower()
    dims = str(raw.get("dimensions", "") or "").strip().lower().replace(" ", "")
    if not name or not dims:
        return None
    return f"{name}|{dims}"


def _ensure_no_duplicate_materials(parameters: dict | None) -> None:
    if not isinstance(parameters, dict):
        return
    materials = parameters.get("materials")
    if not isinstance(materials, list):
        return
    keys: list[str] = []
    for m in materials:
        k = _norm_material_key(m)
        if k:
            keys.append(k)
    if not keys:
        return
    seen: set[str] = set()
    dupes: set[str] = set()
    for k in keys:
        if k in seen:
            dupes.add(k)
        else:
            seen.add(k)
    if dupes:
        raise HTTPException(status_code=400, detail="Duplicate materials are not allowed")


def _parse_num(value: str) -> float:
    if value is None:
        return 0.0
    match = re.search(r"[\d.]+", str(value))
    return float(match.group()) if match else 0.0


def compute_initial_item_weight_kg(item: InitialProjectItem) -> float:
    length = _parse_num(item.length_mm)
    width = _parse_num(item.width_mm)
    thk = _parse_num(item.thk_dia)
    density = _parse_num(item.density_kg_m3)
    qty = _parse_num(item.qty)
    return length * width * thk * density * max(qty, 1) / 1_000_000_000


def resolve_initial_item_weight_kg(item: InitialProjectItem) -> float:
    """Use explicit weight (kg) when provided; otherwise derive from dimensions."""
    explicit = (item.weight_kg or "").strip()
    if explicit:
        return _parse_num(explicit)
    return compute_initial_item_weight_kg(item)


@router.post(
    "/projects",
    response_model=ProjectResponse,
    summary="Add project",
    description=(
        "Creates a new project (unique name). Admin only. "
        "Optional `initial_items` are saved as dashboard line entries. "
        "Returns 409 if the project name already exists."
    ),
)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Admin")),
):
    # Admin API: creates a project.
    existing_project = db.query(Project).filter(Project.name == payload.name).first()
    if existing_project:
        raise HTTPException(status_code=409, detail="Project name already exists")

    _ensure_no_duplicate_materials(payload.parameters)
    project = Project(name=payload.name, parameters=payload.parameters)
    db.add(project)
    db.commit()
    db.refresh(project)

    if payload.initial_items:
        for item in payload.initial_items:
            weight = round(resolve_initial_item_weight_kg(item), 4)
            meta = {
                "user": admin.username,
                "projectType": item.project_type,
                "areaSection": item.area_section,
                "itemDetails": item.item_details,
                "lengthMm": item.length_mm,
                "widthMm": item.width_mm,
                "thkDia": item.thk_dia,
                "densityKgM3": item.density_kg_m3,
                "qty": item.qty,
                "weight": str(weight),
                "weightKg": (item.weight_kg or "").strip(),
                "weldingMeters": item.welding_meters,
                "remarks": item.remarks,
            }
            db.add(
                ProjectData(
                    project_id=project.id,
                    value=float(weight),
                    meta=meta,
                )
            )
        db.commit()
        db.refresh(project)

    return project


@router.get("/projects", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    # Project access API: admin gets all; other roles get assigned projects only.
    if current_user.role == UserRole.ADMIN:
        return db.query(Project).order_by(Project.id.asc()).all()

    return (
        db.query(Project)
        .join(UserProject, UserProject.project_id == Project.id)
        .filter(UserProject.user_id == current_user.id)
        .order_by(Project.id.asc())
        .all()
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    # Admin API: updates project details.
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    _ensure_no_duplicate_materials(payload.parameters)
    project.name = payload.name
    project.parameters = payload.parameters
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    # Admin API: deletes a project by id.
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/assign-user")
def assign_user_to_project(
    payload: AssignUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    # Admin API: assigns a user to a project.
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_assignment = (
        db.query(UserProject)
        .filter(
            UserProject.user_id == payload.user_id,
            UserProject.project_id == payload.project_id,
        )
        .first()
    )
    if existing_assignment:
        raise HTTPException(status_code=409, detail="User already assigned to project")

    assignment = UserProject(user_id=payload.user_id, project_id=payload.project_id)
    db.add(assignment)
    db.commit()
    return {"message": "User assigned to project successfully"}


@router.get("/admin/projects", response_model=AdminProjectsPageResponse)
def get_admin_projects_overview(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    # Admin API: returns paginated projects with assignment and total entry counts.
    project_query = db.query(Project)
    if search:
        project_query = project_query.filter(Project.name.ilike(f"%{search.strip()}%"))

    total = project_query.count()
    projects = (
        project_query.order_by(Project.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    entry_counts = dict(
        db.query(ProjectData.project_id, func.count(ProjectData.id))
        .group_by(ProjectData.project_id)
        .all()
    )

    response: list[AdminProjectOverview] = []
    for project in projects:
        assigned_users = [
            AdminProjectAssignedUser(
                id=assignment.user.id,
                username=assignment.user.username,
                role=assignment.user.role,
            )
            for assignment in project.users
            if assignment.user is not None
        ]
        response.append(
            AdminProjectOverview(
                id=project.id,
                name=project.name,
                parameters=project.parameters,
                total_entries=entry_counts.get(project.id, 0),
                assigned_users=assigned_users,
            )
        )
    return AdminProjectsPageResponse(
        items=response,
        total=total,
        page=page,
        per_page=per_page,
        search=search,
    )


@router.get("/admin/projects/stats", response_model=AdminProjectsStatsResponse)
def get_admin_projects_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_entries = db.query(func.count(ProjectData.id)).scalar() or 0
    active_members = db.query(func.count(distinct(UserProject.user_id))).scalar() or 0
    return AdminProjectsStatsResponse(
        total_projects=int(total_projects),
        total_entries=int(total_entries),
        active_members=int(active_members),
    )


@router.get("/admin/projects/{project_id}", response_model=AdminProjectDetail)
def get_admin_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    # Admin API: returns a project with all chart points and assigned users.
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    points = (
        db.query(ProjectData)
        .filter(ProjectData.project_id == project_id)
        .order_by(ProjectData.timestamp.asc())
        .all()
    )
    assigned_users = [
        AdminProjectAssignedUser(
            id=assignment.user.id,
            username=assignment.user.username,
            role=assignment.user.role,
        )
        for assignment in project.users
        if assignment.user is not None
    ]
    return AdminProjectDetail(
        id=project.id,
        name=project.name,
        parameters=project.parameters,
        total_entries=len(points),
        assigned_users=assigned_users,
        points=[
            DashboardDataPoint(
                id=item.id,
                timestamp=item.timestamp,
                value=item.value,
                meta=item.meta,
            )
            for item in points
        ],
    )
