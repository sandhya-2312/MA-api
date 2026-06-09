from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayrollEmployeePayload(BaseModel):
    serial_no: int = Field(ge=1)
    emp_id: str | None = None
    name: str = Field(min_length=1, max_length=150)
    designation: str | None = None
    # Day values: legacy strings ("P", "P+OT(2)") or {"attendanceStatus", "otHours"} objects.
    attendance: dict[str, Any] | None = None
    ot: str | None = None
    advance: int = 0
    wage: int = 0
    monthly_salary: int = 0
    food: int | None = None
    remarks: str | None = None
    contact_number: str | None = None
    email: str | None = None
    address: str | None = None
    project: str | None = None
    joining_date: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    upi_id: str | None = None
    aadhar_number: str | None = None
    pan_number: str | None = None

    @field_validator("emp_id")
    @classmethod
    def validate_emp_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) != 5 or not cleaned.isdigit():
            raise ValueError("EMP ID must be 5 digits (3-digit prefix + 2-digit year, e.g. 00126)")
        return cleaned


class PayrollEmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    serial_no: int
    emp_id: str | None = None
    name: str
    designation: str | None
    attendance: dict[str, Any] | None
    ot: str | None
    ot_amount: int = 0
    total_ot_hours: float = 0
    ot_rate: int = 0
    advance: int
    wage: int
    monthly_salary: int = 0
    food: int | None
    remarks: str | None
    contact_number: str | None = None
    email: str | None = None
    address: str | None = None
    project: str | None = None
    joining_date: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    upi_id: str | None = None
    aadhar_number: str | None = None
    pan_number: str | None = None
    total_days: float
    final_payment: int


class PayrollModuleCreateRequest(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    location: str | None = "Maruti -1 Drydock"
    company_name: str | None = "MC.Engg"
    copy_from_module_id: int | None = None


class PayrollModuleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    month: int
    year: int
    location: str | None
    company_name: str | None
    employee_count: int
    total_final_payment: int


class PayrollModuleDetail(PayrollModuleSummary):
    weekday_labels: list[str]
    days_in_month: int
    employees: list[PayrollEmployeeResponse]


class PayrollLocationsResponse(BaseModel):
    locations: list[str]


class PayrollCompaniesResponse(BaseModel):
    companies: list[str]


class PayrollProjectAttendanceSummary(BaseModel):
    module_id: int
    project: str
    company_name: str | None
    employee_count: int
    present_days: int
    ot_hours: float
    absent_days: int
    half_days: int


class PayrollAttendanceSummaryResponse(BaseModel):
    month: int
    year: int
    company_name: str | None
    projects: list[PayrollProjectAttendanceSummary]
    total_present_days: int
    total_ot_hours: float
    total_absent_days: int
    total_half_days: int
    total_employees: int
