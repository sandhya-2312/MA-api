from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PayrollEmployee, PayrollModule, User
from backend.schemas.payroll import (
    PayrollAttendanceSummaryResponse,
    PayrollEmployeePayload,
    PayrollEmployeeResponse,
    PayrollCompaniesResponse,
    PayrollLocationsResponse,
    PayrollModuleCreateRequest,
    PayrollModuleDetail,
    PayrollModuleSummary,
    PayrollProjectAttendanceSummary,
)
from backend.services.attendance import (
    calc_ot_amount,
    count_attendance_breakdown,
    count_total_ot_hours,
    derive_pay_rates_from_monthly_salary,
    parse_ot_rate,
)
from backend.services.payroll_calc import (
    count_total_days,
    days_in_month,
    final_payment,
    weekday_labels,
)
from backend.services.payroll_excel import build_payroll_workbook
from backend.utils.auth import require_roles

router = APIRouter(tags=["Payroll"])

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

DEFAULT_LOCATIONS = ["Maruti -1 Drydock", "Maruti -2 Drydock", "Yard Office"]
DEFAULT_COMPANIES = ["MC.Engineering"]


def _norm_location(value: str | None) -> str:
    return (value or "").strip() or DEFAULT_LOCATIONS[0]


def _norm_company(value: str | None) -> str:
    return (value or "").strip() or DEFAULT_COMPANIES[0]


def _company_name_filter(company: str):
    if company == DEFAULT_COMPANIES[0]:
        return or_(
            PayrollModule.company_name == company,
            PayrollModule.company_name == "MC.Engg",
            PayrollModule.company_name.is_(None),
            PayrollModule.company_name == "",
        )
    return PayrollModule.company_name == company


def _module_title(month: int, year: int, location: str | None, company_name: str | None) -> str:
    month_label = MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
    loc = _norm_location(location)
    return f"{(company_name or 'MC.Engineering').strip()} Payroll : {month_label} {year} ( {loc} )"


def _strip_optional(value: str | None, *, max_len: int | None = None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    if max_len is not None:
        return cleaned[:max_len]
    return cleaned


def _format_emp_id(prefix: int, year: int) -> str:
    return f"{prefix:03d}{year % 100:02d}"


def _emp_id_year(joining_date: str | None, module: PayrollModule | None) -> int:
    if joining_date and len(joining_date) >= 4:
        try:
            return int(joining_date[:4])
        except ValueError:
            pass
    return module.year if module else 2000


def _next_emp_id(db: Session, year: int) -> str:
    year_suffix = f"{year % 100:02d}"
    rows = (
        db.query(PayrollEmployee.emp_id)
        .filter(PayrollEmployee.emp_id.isnot(None), PayrollEmployee.emp_id.like(f"%{year_suffix}"))
        .all()
    )
    max_prefix = 0
    for (emp_id,) in rows:
        if emp_id and len(emp_id) == 5 and emp_id.endswith(year_suffix):
            try:
                max_prefix = max(max_prefix, int(emp_id[:3]))
            except ValueError:
                continue
    return _format_emp_id(max_prefix + 1, year)


def _sync_derived_pay_rates(row: PayrollEmployee, module: PayrollModule | None) -> None:
    monthly = row.monthly_salary or 0
    if monthly <= 0 or not module:
        return
    dim = days_in_month(module.year, module.month)
    if dim <= 0:
        return
    wage, ot_rate = derive_pay_rates_from_monthly_salary(monthly, dim)
    row.wage = wage
    row.ot = str(ot_rate)


def _resolved_pay_rates(row: PayrollEmployee, module: PayrollModule | None) -> tuple[int, str | None]:
    monthly = row.monthly_salary or 0
    if monthly > 0 and module:
        dim = days_in_month(module.year, module.month)
        if dim > 0:
            wage, ot_rate = derive_pay_rates_from_monthly_salary(monthly, dim)
            return wage, str(ot_rate)
    return row.wage or 0, row.ot


def _apply_employee_payload(
    row: PayrollEmployee,
    payload: PayrollEmployeePayload,
    *,
    module: PayrollModule | None = None,
    db: Session | None = None,
    auto_emp_id: bool = False,
) -> None:
    row.serial_no = payload.serial_no
    if payload.emp_id:
        row.emp_id = payload.emp_id
    elif auto_emp_id and db is not None and module is not None:
        year = _emp_id_year(payload.joining_date, module)
        row.emp_id = _next_emp_id(db, year)
    row.name = payload.name.strip()
    row.designation = _strip_optional(payload.designation, max_len=100)
    row.attendance = payload.attendance or {}
    row.ot = str(payload.ot or "") or None
    row.advance = payload.advance
    row.wage = payload.wage
    row.monthly_salary = payload.monthly_salary
    row.food = payload.food
    row.remarks = _strip_optional(payload.remarks, max_len=100)
    row.contact_number = _strip_optional(payload.contact_number, max_len=20)
    row.email = _strip_optional(payload.email, max_len=255)
    row.address = _strip_optional(payload.address, max_len=500)
    row.project = _strip_optional(payload.project, max_len=200)
    row.joining_date = _strip_optional(payload.joining_date, max_len=20)
    row.bank_name = _strip_optional(payload.bank_name, max_len=150)
    row.account_number = _strip_optional(payload.account_number, max_len=50)
    row.ifsc_code = _strip_optional(payload.ifsc_code, max_len=20)
    row.upi_id = _strip_optional(payload.upi_id, max_len=100)
    row.aadhar_number = _strip_optional(payload.aadhar_number, max_len=12)
    row.pan_number = _strip_optional(payload.pan_number, max_len=10)


def _employee_response(row: PayrollEmployee, module: PayrollModule | None = None) -> PayrollEmployeeResponse:
    attendance = row.attendance if isinstance(row.attendance, dict) else None
    total_days = count_total_days(attendance)
    total_ot_hours = count_total_ot_hours(attendance)
    mod = module or row.module
    wage, ot = _resolved_pay_rates(row, mod)
    ot_rate = parse_ot_rate(ot)
    ot_amount = calc_ot_amount(total_ot_hours, ot_rate)
    dim = days_in_month(mod.year, mod.month) if mod else 0
    payment = final_payment(
        total_days,
        wage,
        ot_amount,
        row.advance or 0,
        row.food,
        monthly_salary=row.monthly_salary or 0,
        days_in_month=dim,
    )
    return PayrollEmployeeResponse(
        id=row.id,
        module_id=row.module_id,
        serial_no=row.serial_no,
        emp_id=row.emp_id,
        name=row.name,
        designation=row.designation,
        attendance=attendance,
        ot=ot,
        ot_amount=ot_amount,
        total_ot_hours=total_ot_hours,
        ot_rate=ot_rate,
        advance=row.advance or 0,
        wage=wage,
        monthly_salary=row.monthly_salary or 0,
        food=row.food,
        remarks=row.remarks,
        contact_number=row.contact_number,
        email=row.email,
        address=row.address,
        project=row.project,
        joining_date=row.joining_date,
        bank_name=row.bank_name,
        account_number=row.account_number,
        ifsc_code=row.ifsc_code,
        upi_id=row.upi_id,
        aadhar_number=row.aadhar_number,
        pan_number=row.pan_number,
        total_days=total_days,
        final_payment=payment,
    )


def _module_detail(module: PayrollModule, employees: list[PayrollEmployee]) -> PayrollModuleDetail:
    summary = _module_summary(module, employees)
    return PayrollModuleDetail(
        **summary.model_dump(),
        weekday_labels=weekday_labels(module.year, module.month),
        days_in_month=days_in_month(module.year, module.month),
        employees=[_employee_response(emp, module) for emp in employees],
    )


def _module_summary(module: PayrollModule, employees: list[PayrollEmployee]) -> PayrollModuleSummary:
    total_payment = sum(_employee_response(emp, module).final_payment for emp in employees)
    return PayrollModuleSummary(
        id=module.id,
        title=_module_title(module.month, module.year, module.location, module.company_name),
        month=module.month,
        year=module.year,
        location=module.location,
        company_name=module.company_name,
        employee_count=len(employees),
        total_final_payment=total_payment,
    )


def _find_module(
    db: Session,
    *,
    month: int,
    year: int,
    location: str | None,
    company_name: str | None = None,
) -> PayrollModule | None:
    loc = _norm_location(location)
    company = _norm_company(company_name)
    return (
        db.query(PayrollModule)
        .filter(
            PayrollModule.month == month,
            PayrollModule.year == year,
            PayrollModule.location == loc,
            _company_name_filter(company),
        )
        .first()
    )


@router.get("/payroll/locations", response_model=PayrollLocationsResponse)
def list_payroll_locations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    rows = db.query(PayrollModule.location).distinct().all()
    found = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()})
    merged = list(dict.fromkeys([*DEFAULT_LOCATIONS, *found]))
    return PayrollLocationsResponse(locations=merged)


@router.get("/payroll/companies", response_model=PayrollCompaniesResponse)
def list_payroll_companies(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    rows = db.query(PayrollModule.company_name).distinct().all()
    found = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()})
    merged = list(dict.fromkeys([*DEFAULT_COMPANIES, *found]))
    return PayrollCompaniesResponse(companies=merged)


@router.get("/payroll/attendance-summary", response_model=PayrollAttendanceSummaryResponse)
def payroll_attendance_summary(
    month: Annotated[int, Query(ge=1, le=12)],
    year: Annotated[int, Query(ge=2000, le=2100)],
    company_name: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    company = _norm_company(company_name) if company_name and company_name.strip() else None
    query = db.query(PayrollModule).filter(
        PayrollModule.month == month,
        PayrollModule.year == year,
    )
    if company:
        query = query.filter(_company_name_filter(company))

    modules = query.order_by(PayrollModule.location.asc()).all()
    projects: list[PayrollProjectAttendanceSummary] = []
    total_present = 0
    total_ot = 0.0
    total_absent = 0
    total_half = 0
    total_employees = 0

    for module in modules:
        employees = (
            db.query(PayrollEmployee)
            .filter(PayrollEmployee.module_id == module.id)
            .all()
        )
        present = absent = half = 0
        ot_hours = 0.0
        for emp in employees:
            breakdown = count_attendance_breakdown(
                emp.attendance if isinstance(emp.attendance, dict) else None
            )
            present += int(breakdown["present_days"])
            absent += int(breakdown["absent_days"])
            half += int(breakdown["half_days"])
            ot_hours += float(breakdown["ot_hours"])

        ot_hours = round(ot_hours, 1)
        projects.append(
            PayrollProjectAttendanceSummary(
                module_id=module.id,
                project=_norm_location(module.location),
                company_name=module.company_name,
                employee_count=len(employees),
                present_days=present,
                ot_hours=ot_hours,
                absent_days=absent,
                half_days=half,
            )
        )
        total_present += present
        total_ot += ot_hours
        total_absent += absent
        total_half += half
        total_employees += len(employees)

    return PayrollAttendanceSummaryResponse(
        month=month,
        year=year,
        company_name=company,
        projects=projects,
        total_present_days=total_present,
        total_ot_hours=round(total_ot, 1),
        total_absent_days=total_absent,
        total_half_days=total_half,
        total_employees=total_employees,
    )


@router.get("/payroll/modules", response_model=list[PayrollModuleSummary])
def list_payroll_modules(
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    location: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    query = db.query(PayrollModule)
    if month is not None:
        query = query.filter(PayrollModule.month == month)
    if year is not None:
        query = query.filter(PayrollModule.year == year)
    if location is not None and location.strip():
        query = query.filter(PayrollModule.location == _norm_location(location))

    modules = query.order_by(PayrollModule.year.desc(), PayrollModule.month.desc()).all()
    result: list[PayrollModuleSummary] = []
    for module in modules:
        employees = (
            db.query(PayrollEmployee)
            .filter(PayrollEmployee.module_id == module.id)
            .order_by(PayrollEmployee.serial_no)
            .all()
        )
        result.append(_module_summary(module, employees))
    return result


@router.get("/payroll/modules/resolve", response_model=PayrollModuleDetail | None)
def resolve_payroll_module(
    month: Annotated[int, Query(ge=1, le=12)],
    year: Annotated[int, Query(ge=2000, le=2100)],
    location: Annotated[str | None, Query()] = None,
    company_name: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    module = _find_module(
        db,
        month=month,
        year=year,
        location=location,
        company_name=company_name,
    )
    if not module:
        return None
    employees = (
        db.query(PayrollEmployee)
        .filter(PayrollEmployee.module_id == module.id)
        .order_by(PayrollEmployee.serial_no)
        .all()
    )
    return _module_detail(module, employees)


@router.post("/payroll/modules", response_model=PayrollModuleDetail)
def create_payroll_module(
    payload: PayrollModuleCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    loc = _norm_location(payload.location)
    company = _norm_company(payload.company_name)
    existing = _find_module(
        db,
        month=payload.month,
        year=payload.year,
        location=loc,
        company_name=company,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A payroll sheet for this company, project, month, and year already exists",
        )

    title = _module_title(payload.month, payload.year, loc, company)
    module = PayrollModule(
        title=title,
        month=payload.month,
        year=payload.year,
        location=loc,
        company_name=company,
    )
    db.add(module)
    db.flush()

    if payload.copy_from_module_id:
        source_rows = (
            db.query(PayrollEmployee)
            .filter(PayrollEmployee.module_id == payload.copy_from_module_id)
            .order_by(PayrollEmployee.serial_no)
            .all()
        )
        for src in source_rows:
            db.add(
                PayrollEmployee(
                    module_id=module.id,
                    serial_no=src.serial_no,
                    emp_id=src.emp_id,
                    name=src.name,
                    designation=src.designation,
                    attendance={},
                    advance=src.advance,
                    wage=src.wage,
                    monthly_salary=src.monthly_salary,
                    food=src.food,
                    remarks=src.remarks,
                    contact_number=src.contact_number,
                    email=src.email,
                    address=src.address,
                    project=src.project,
                    joining_date=src.joining_date,
                    bank_name=src.bank_name,
                    account_number=src.account_number,
                    ifsc_code=src.ifsc_code,
                    upi_id=src.upi_id,
                    aadhar_number=src.aadhar_number,
                    pan_number=src.pan_number,
                )
            )

    db.commit()
    db.refresh(module)
    employees = (
        db.query(PayrollEmployee)
        .filter(PayrollEmployee.module_id == module.id)
        .order_by(PayrollEmployee.serial_no)
        .all()
    )
    return _module_detail(module, employees)


@router.get("/payroll/modules/{module_id}", response_model=PayrollModuleDetail)
def get_payroll_module(
    module_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    module = db.query(PayrollModule).filter(PayrollModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Payroll module not found")

    employees = (
        db.query(PayrollEmployee)
        .filter(PayrollEmployee.module_id == module.id)
        .order_by(PayrollEmployee.serial_no)
        .all()
    )
    return _module_detail(module, employees)


@router.get("/payroll/modules/{module_id}/export")
def export_payroll_module(
    module_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    module = db.query(PayrollModule).filter(PayrollModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Payroll module not found")

    employees = (
        db.query(PayrollEmployee)
        .filter(PayrollEmployee.module_id == module.id)
        .order_by(PayrollEmployee.serial_no)
        .all()
    )
    responses = [_employee_response(emp, module) for emp in employees]
    xlsx_bytes = build_payroll_workbook(module, employees, responses)
    filename = f"salaries_{module.year}_{module.month:02d}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/payroll/modules/{module_id}")
def delete_payroll_module(
    module_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    module = db.query(PayrollModule).filter(PayrollModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Payroll module not found")
    db.delete(module)
    db.commit()
    return {"ok": True}


@router.post("/payroll/modules/{module_id}/employees", response_model=PayrollEmployeeResponse)
def add_payroll_employee(
    module_id: int,
    payload: PayrollEmployeePayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    module = db.query(PayrollModule).filter(PayrollModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Payroll module not found")

    row = PayrollEmployee(module_id=module.id)
    _apply_employee_payload(row, payload, module=module, db=db, auto_emp_id=True)
    _sync_derived_pay_rates(row, module)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _employee_response(row, module)


@router.put("/payroll/employees/{employee_id}", response_model=PayrollEmployeeResponse)
def update_payroll_employee(
    employee_id: int,
    payload: PayrollEmployeePayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    row = db.query(PayrollEmployee).filter(PayrollEmployee.id == employee_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Employee row not found")

    _apply_employee_payload(row, payload)
    module = db.query(PayrollModule).filter(PayrollModule.id == row.module_id).first()
    _sync_derived_pay_rates(row, module)
    db.commit()
    db.refresh(row)
    return _employee_response(row, module)


@router.delete("/payroll/employees/{employee_id}")
def delete_payroll_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
):
    row = db.query(PayrollEmployee).filter(PayrollEmployee.id == employee_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Employee row not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
