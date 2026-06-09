"""Attendance parsing and payroll day/OT calculations."""

from __future__ import annotations

from typing import Any


def _parse_ot_hours(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        n = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, round(n, 1))


def parse_day_entry(raw: Any) -> tuple[str, float]:
    """Return (attendance_status, ot_hours). Status: '', 'P', 'A', 'H', 'P+OT'."""
    if isinstance(raw, dict):
        status_raw = str(raw.get("attendanceStatus") or raw.get("status") or "").strip().upper()
        ot_hours = _parse_ot_hours(raw.get("otHours") if "otHours" in raw else raw.get("ot_hours"))
        if status_raw in ("P+OT", "POT", "OT"):
            return "P+OT", ot_hours
        if status_raw in ("P", "1"):
            return "P", 0.0
        if status_raw == "A":
            return "A", 0.0
        if status_raw == "H":
            return "H", 0.0
        return "", 0.0

    token = str(raw or "").strip().upper()
    if not token or token in (".", "·"):
        return "", 0.0
    if token in ("P", "1"):
        return "P", 0.0
    if token == "A":
        return "A", 0.0
    if token == "H":
        return "H", 0.0
    if token.startswith("P+OT") or token == "OT":
        if "(" in token:
            inner = token.split("(", 1)[1].rstrip(")")
            return "P+OT", _parse_ot_hours(inner)
        return "P+OT", 0.0
    return "", 0.0


def day_working_points(status: str) -> float:
    if status in ("P", "P+OT"):
        return 1.0
    if status == "H":
        return 0.5
    return 0.0


def count_total_days(attendance: dict | None) -> float:
    if not isinstance(attendance, dict):
        return 0.0
    total = sum(day_working_points(parse_day_entry(value)[0]) for value in attendance.values())
    return round(total, 1)


def count_total_ot_hours(attendance: dict | None) -> float:
    if not isinstance(attendance, dict):
        return 0.0
    total = 0.0
    for value in attendance.values():
        status, ot_hours = parse_day_entry(value)
        if status == "P+OT":
            total += ot_hours
    return round(total, 1)


def count_attendance_breakdown(attendance: dict | None) -> dict[str, int | float]:
    """Count day marks: P/P+OT as present, A absent, H half-day; sum OT hours."""
    present_days = 0
    absent_days = 0
    half_days = 0
    ot_hours = 0.0
    if not isinstance(attendance, dict):
        return {
            "present_days": 0,
            "absent_days": 0,
            "half_days": 0,
            "ot_hours": 0.0,
        }

    for value in attendance.values():
        status, hours = parse_day_entry(value)
        if status in ("P", "P+OT"):
            present_days += 1
            if status == "P+OT":
                ot_hours += hours
        elif status == "A":
            absent_days += 1
        elif status == "H":
            half_days += 1

    return {
        "present_days": present_days,
        "absent_days": absent_days,
        "half_days": half_days,
        "ot_hours": round(ot_hours, 1),
    }


def parse_ot_rate(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return max(0, int(round(float(str(value).replace(",", "").strip()))))
    except (TypeError, ValueError):
        return 0


def calc_ot_amount(total_ot_hours: float, ot_rate: int) -> int:
    return int(round(total_ot_hours * (ot_rate or 0)))


def format_day_label(raw: Any) -> str:
    status, ot_hours = parse_day_entry(raw)
    if not status:
        return ""
    if status == "P+OT":
        if ot_hours > 0:
            h = int(ot_hours) if ot_hours == int(ot_hours) else ot_hours
            return f"P+OT({h})"
        return "P+OT"
    return status


def derive_pay_rates_from_monthly_salary(monthly_salary: int, days_in_month: int) -> tuple[int, int]:
    """Daily wage = monthly ÷ days in month; OT/hour = daily wage ÷ 8."""
    if monthly_salary <= 0 or days_in_month <= 0:
        return 0, 0
    wage = round(monthly_salary / days_in_month)
    ot_rate = round(wage / 8)
    return wage, ot_rate


def calc_base_pay(
    total_days: float,
    wage: int,
    *,
    monthly_salary: int = 0,
    days_in_month: int = 0,
) -> int:
    """Daily wage workers use wage × days; monthly salaried use pro-rated monthly_salary."""
    if monthly_salary > 0 and wage <= 0 and days_in_month > 0:
        return round(total_days * (monthly_salary / days_in_month))
    return round(total_days * (wage or 0))


def final_payment(
    total_days: float,
    wage: int,
    ot_amount: int,
    advance: int,
    food: int | None = None,
    *,
    monthly_salary: int = 0,
    days_in_month: int = 0,
) -> int:
    base = calc_base_pay(
        total_days,
        wage,
        monthly_salary=monthly_salary,
        days_in_month=days_in_month,
    )
    food_amount = food or 0
    return max(0, base + (ot_amount or 0) - (advance or 0) - food_amount)
