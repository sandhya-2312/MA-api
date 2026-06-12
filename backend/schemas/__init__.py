from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    first_login: bool


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    username: str
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str
    temporary_password: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserCreateRequest(BaseModel):
    username: str
    password: str = Field(min_length=8)
    role: UserRole
    project_ids: list[int] = []
    contact_no: str | None = None
    full_name: str | None = None
    email: str | None = None
    designation: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    first_login: bool
    assigned_project_ids: list[int] = []
    contact_no: str | None = None
    full_name: str | None = None
    email: str | None = None
    designation: str | None = None
    access_token: str | None = None


class UserCreateResponse(BaseModel):
    user: UserResponse
    temporary_password: str | None = None


class InitialProjectItem(BaseModel):
    """One steel-renewal line item stored as project_data + meta."""

    project_type: str = ""
    area_section: str = ""
    item_details: str = ""
    length_mm: str = ""
    width_mm: str = ""
    thk_dia: str = ""
    density_kg_m3: str = ""
    qty: str = ""
    weight_kg: str = ""
    welding_meters: str = ""
    remarks: str = ""


class ProjectCreateRequest(BaseModel):
    name: str
    parameters: dict[str, Any] | None = None
    initial_items: list[InitialProjectItem] | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parameters: dict[str, Any] | None


class AssignUserRequest(BaseModel):
    user_id: int
    project_id: int


class ProjectDataCreateRequest(BaseModel):
    project_id: int
    value: float
    timestamp: datetime | None = None
    meta: dict[str, Any] | None = None


class ProjectDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    value: float
    timestamp: datetime
    meta: dict[str, Any] | None = None


class DashboardDataPoint(BaseModel):
    id: int
    timestamp: datetime
    value: float
    meta: dict[str, Any] | None = None


class DashboardDataResponse(BaseModel):
    project_id: int
    project_name: str
    points: list[DashboardDataPoint]


class BulkDashboardProjectData(BaseModel):
    project_id: int
    points: list[DashboardDataPoint]


class BulkDashboardDataResponse(BaseModel):
    items: list[BulkDashboardProjectData]


class ProfileUpdateRequest(BaseModel):
    username: str
    new_password: str | None = Field(default=None, min_length=8)
    contact_no: str | None = None
    full_name: str | None = None
    email: str | None = None
    designation: str | None = None


class UserUpdateRequest(BaseModel):
    username: str
    role: UserRole
    project_ids: list[int] = []
    contact_no: str | None = None
    full_name: str | None = None
    email: str | None = None
    designation: str | None = None


class ProjectDataUpdateRequest(BaseModel):
    value: float
    meta: dict[str, Any] | None = None


class AdminProjectAssignedUser(BaseModel):
    id: int
    username: str
    role: UserRole


class AdminProjectOverview(BaseModel):
    id: int
    name: str
    parameters: dict[str, Any] | None
    total_entries: int
    assigned_users: list[AdminProjectAssignedUser]


class AdminProjectDetail(AdminProjectOverview):
    points: list[DashboardDataPoint]


class AdminProjectsPageResponse(BaseModel):
    items: list[AdminProjectOverview]
    total: int
    page: int
    per_page: int
    search: str | None = None


class AdminProjectsStatsResponse(BaseModel):
    total_projects: int
    total_entries: int
    active_members: int
