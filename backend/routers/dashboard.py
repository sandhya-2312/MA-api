from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.enums import UserRole
from backend.models import Project, ProjectData, User, UserProject
from backend.schemas import (
    BulkDashboardDataResponse,
    BulkDashboardProjectData,
    DashboardDataPoint,
    DashboardDataResponse,
    ProjectDataCreateRequest,
    ProjectDataResponse,
    ProjectDataUpdateRequest,
)
from backend.services.material_weight import validate_entry_meta
from backend.utils.auth import require_roles

router = APIRouter(tags=["Dashboard and Data"])


def _validated_entry_value_and_meta(meta: dict | None, submitted_value: float) -> tuple[float, dict]:
    weight, errors = validate_entry_meta(meta)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    normalized = dict(meta or {})
    normalized["weight"] = str(weight)
    if abs(float(submitted_value) - weight) > 0.05:
        raise HTTPException(
            status_code=400,
            detail=f"Submitted value ({submitted_value}) does not match calculated weight ({weight} kg).",
        )
    return weight, normalized


@router.post("/data", response_model=ProjectDataResponse)
def add_project_data(
    payload: ProjectDataCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User")),
):
    # Data API: users/admins add project data entries.
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN:
        assignment = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user.id,
                UserProject.project_id == payload.project_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Project not assigned to user")

    value, meta = _validated_entry_value_and_meta(payload.meta, payload.value)
    new_data = ProjectData(
        project_id=payload.project_id,
        value=value,
        timestamp=payload.timestamp,
        meta=meta,
    )
    db.add(new_data)
    db.commit()
    db.refresh(new_data)
    return new_data


@router.get("/dashboard-data", response_model=DashboardDataResponse)
def get_dashboard_data(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    # Dashboard API: returns chart-ready data for a project.
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN:
        assignment = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user.id,
                UserProject.project_id == project_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Project not assigned to user")

    points = (
        db.query(ProjectData)
        .filter(ProjectData.project_id == project_id)
        .order_by(ProjectData.timestamp.asc())
        .all()
    )

    return DashboardDataResponse(
        project_id=project.id,
        project_name=project.name,
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


@router.put("/data/{data_id}", response_model=ProjectDataResponse)
def update_project_data(
    data_id: int,
    payload: ProjectDataUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User")),
):
    # Data API: updates an existing project data value.
    data_entry = db.query(ProjectData).filter(ProjectData.id == data_id).first()
    if not data_entry:
        raise HTTPException(status_code=404, detail="Data entry not found")

    if current_user.role != UserRole.ADMIN:
        assignment = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user.id,
                UserProject.project_id == data_entry.project_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Project not assigned to user")

    if payload.meta is not None:
        value, meta = _validated_entry_value_and_meta(payload.meta, payload.value)
        data_entry.value = value
        data_entry.meta = meta
    else:
        data_entry.value = payload.value
    db.commit()
    db.refresh(data_entry)
    return data_entry


@router.delete("/data/{data_id}")
def delete_project_data(
    data_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User")),
):
    data_entry = db.query(ProjectData).filter(ProjectData.id == data_id).first()
    if not data_entry:
        raise HTTPException(status_code=404, detail="Data entry not found")

    if current_user.role != UserRole.ADMIN:
        assignment = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user.id,
                UserProject.project_id == data_entry.project_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Project not assigned to user")

    db.delete(data_entry)
    db.commit()
    return {"message": "Data entry deleted successfully"}


@router.get("/dashboard-data/bulk", response_model=BulkDashboardDataResponse)
def get_dashboard_data_bulk(
    project_ids: str | None = Query(default=None, description="Comma-separated project ids"),
    from_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    to_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    requested_ids: list[int] = []
    if project_ids and project_ids.strip():
        try:
            requested_ids = [int(part.strip()) for part in project_ids.split(",") if part.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project_ids query") from exc

    if current_user.role == UserRole.ADMIN:
        accessible_ids = {row[0] for row in db.query(Project.id).all()}
    else:
        accessible_ids = {
            row[0]
            for row in db.query(UserProject.project_id).filter(UserProject.user_id == current_user.id).all()
        }

    selected_ids = sorted((set(requested_ids) if requested_ids else accessible_ids) & accessible_ids)
    if requested_ids and not selected_ids:
        return BulkDashboardDataResponse(items=[])

    date_from = None
    date_to_exclusive = None
    try:
        if from_date:
            date_from = datetime.fromisoformat(f"{from_date}T00:00:00")
        if to_date:
            date_to_exclusive = datetime.fromisoformat(f"{to_date}T00:00:00") + timedelta(days=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from exc

    query = db.query(ProjectData).filter(ProjectData.project_id.in_(selected_ids))
    if date_from is not None:
        query = query.filter(ProjectData.timestamp >= date_from)
    if date_to_exclusive is not None:
        query = query.filter(ProjectData.timestamp < date_to_exclusive)

    points = query.order_by(ProjectData.project_id.asc(), ProjectData.timestamp.asc()).all()
    grouped: dict[int, list[DashboardDataPoint]] = {project_id: [] for project_id in selected_ids}
    for item in points:
        grouped[item.project_id].append(
            DashboardDataPoint(
                id=item.id,
                timestamp=item.timestamp,
                value=item.value,
                meta=item.meta,
            )
        )

    return BulkDashboardDataResponse(
        items=[BulkDashboardProjectData(project_id=project_id, points=grouped[project_id]) for project_id in selected_ids]
    )


@router.get("/reports/project/{project_id}/summary")
def export_project_summary_report(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN:
        assignment = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user.id,
                UserProject.project_id == project_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Project not assigned to user")

    points = (
        db.query(ProjectData)
        .filter(ProjectData.project_id == project_id)
        .order_by(ProjectData.timestamp.asc())
        .all()
    )

    lines = [
        "Project Name,Timestamp,User,Area/Section,Item,Dimensions,Qty,Weight (kg),Welding (m),Remarks",
    ]
    for item in points:
        meta = item.meta or {}
        line = [
            project.name,
            str(item.timestamp.isoformat() if item.timestamp else ""),
            str(meta.get("user", "")),
            str(meta.get("areaSection", "")),
            str(meta.get("itemDetails", "")),
            str(meta.get("dimensions", "")),
            str(meta.get("qty", "")),
            str(meta.get("weight", item.value)),
            str(meta.get("weldingMeters", "")),
            str(meta.get("remarks", "")),
        ]
        escaped = [f"\"{str(value).replace('\"', '\"\"')}\"" for value in line]
        lines.append(",".join(escaped))

    csv_content = "\n".join(lines)
    filename = f"project_{project_id}_summary.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
