from pydantic import BaseModel, ConfigDict, Field


class PayrollEmployeePayload(BaseModel):
    serial_no: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=150)
    designation: str | None = None
    attendance: dict[str, str] | None = None
    ot: str | None = None
    advance: int = 0
    wage: int = 0
    food: int | None = None
    remarks: str | None = None


class PayrollEmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    serial_no: int
    name: str
    designation: str | None
    attendance: dict[str, str] | None
    ot: str | None
    ot_amount: int = 0
    advance: int
    wage: int
    food: int | None
    remarks: str | None
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
