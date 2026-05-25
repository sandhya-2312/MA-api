from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PayrollEmployee, PayrollModule, User
from backend.schemas.payroll import (
    PayrollEmployeePayload,
    PayrollEmployeeResponse,
    PayrollLocationsResponse,
    PayrollModuleCreateRequest,
    PayrollModuleDetail,
    PayrollModuleSummary,
)
from backend.services.payroll_calc import (
    count_total_days,
    days_in_month,
    final_payment,
    parse_ot_amount,
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


def _norm_location(value: str | None) -> str:
    return (value or "").strip() or DEFAULT_LOCATIONS[0]


def _module_title(month: int, year: int, location: str | None, company_name: str | None) -> str:
    month_label = MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
    loc = _norm_location(location)
    return f"{(company_name or 'MC.Engg').strip()} Salaries : {month_label} {year} ( {loc} )"


def _employee_response(row: PayrollEmployee) -> PayrollEmployeeResponse:
    total_days = count_total_days(row.attendance)
    ot_amount = parse_ot_amount(row.ot)
    payment = final_payment(total_days, row.wage or 0, ot_amount, row.advance or 0, row.food)
    return PayrollEmployeeResponse(
        id=row.id,
        module_id=row.module_id,
        serial_no=row.serial_no,
        name=row.name,
        designation=row.designation,
        attendance=row.attendance if isinstance(row.attendance, dict) else None,
        ot=row.ot,
        ot_amount=ot_amount,
        advance=row.advance or 0,
        wage=row.wage or 0,
        food=row.food,
        remarks=row.remarks,
        total_days=total_days,
        final_payment=payment,
    )


def _module_detail(module: PayrollModule, employees: list[PayrollEmployee]) -> PayrollModuleDetail:
    summary = _module_summary(module, employees)
    return PayrollModuleDetail(
        **summary.model_dump(),
        weekday_labels=weekday_labels(module.year, module.month),
        days_in_month=days_in_month(module.year, module.month),
        employees=[_employee_response(emp) for emp in employees],
    )


def _module_summary(module: PayrollModule, employees: list[PayrollEmployee]) -> PayrollModuleSummary:
    total_payment = sum(_employee_response(emp).final_payment for emp in employees)
    return PayrollModuleSummary(
        id=module.id,
        title=module.title,
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
) -> PayrollModule | None:
    loc = _norm_location(location)
    return (
        db.query(PayrollModule)
        .filter(
            PayrollModule.month == month,
            PayrollModule.year == year,
            PayrollModule.location == loc,
        )
        .first()
    )


@router.get("/payroll/locations", response_model=PayrollLocationsResponse)
def list_payroll_locations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    rows = db.query(PayrollModule.location).distinct().all()
    found = sorted({(row[0] or "").strip() for row in rows if (row[0] or "").strip()})
    merged = list(dict.fromkeys([*DEFAULT_LOCATIONS, *found]))
    return PayrollLocationsResponse(locations=merged)


@router.get("/payroll/modules", response_model=list[PayrollModuleSummary])
def list_payroll_modules(
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    location: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "User", "Viewer")),
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
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "User", "Viewer")),
):
    module = _find_module(db, month=month, year=year, location=location)
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
    _: User = Depends(require_roles("Admin", "User")),
):
    loc = _norm_location(payload.location)
    existing = _find_module(db, month=payload.month, year=payload.year, location=loc)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A payroll sheet for this month, year, and project already exists",
        )

    title = _module_title(payload.month, payload.year, loc, payload.company_name)
    module = PayrollModule(
        title=title,
        month=payload.month,
        year=payload.year,
        location=loc,
        company_name=payload.company_name,
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
                    name=src.name,
                    designation=src.designation,
                    attendance={},
                    advance=src.advance,
                    wage=src.wage,
                    food=src.food,
                    remarks=src.remarks,
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
    _: User = Depends(require_roles("Admin", "User", "Viewer")),
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
    _: User = Depends(require_roles("Admin", "User", "Viewer")),
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
    responses = [_employee_response(emp) for emp in employees]
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
    _: User = Depends(require_roles("Admin", "User")),
):
    module = db.query(PayrollModule).filter(PayrollModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Payroll module not found")

    row = PayrollEmployee(
        module_id=module.id,
        serial_no=payload.serial_no,
        name=payload.name.strip(),
        designation=(payload.designation or "").strip() or None,
        attendance=payload.attendance or {},
        ot=str(payload.ot or "") or None,
        advance=payload.advance,
        wage=payload.wage,
        food=payload.food,
        remarks=payload.remarks,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _employee_response(row)


@router.put("/payroll/employees/{employee_id}", response_model=PayrollEmployeeResponse)
def update_payroll_employee(
    employee_id: int,
    payload: PayrollEmployeePayload,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "User")),
):
    row = db.query(PayrollEmployee).filter(PayrollEmployee.id == employee_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Employee row not found")

    row.serial_no = payload.serial_no
    row.name = payload.name.strip()
    row.designation = (payload.designation or "").strip() or None
    row.attendance = payload.attendance or {}
    row.ot = str(payload.ot or "") or None
    row.advance = payload.advance
    row.wage = payload.wage
    row.food = payload.food
    row.remarks = payload.remarks
    db.commit()
    db.refresh(row)
    return _employee_response(row)


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
