from calendar import monthrange
from datetime import date

ATTENDANCE_PRESENT = frozenset({"P", "1"})
ATTENDANCE_HALF = frozenset({"H"})
ATTENDANCE_ABSENT = frozenset({"A"})
ATTENDANCE_OT_DAY = frozenset({"OT"})


def days_in_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def weekday_labels(year: int, month: int) -> list[str]:
    """Return short weekday names (Sun–Sat) for each calendar day in the month."""
    count = days_in_month(year, month)
    return [date(year, month, day).strftime("%a") for day in range(1, count + 1)]


def _day_value_points(raw: object) -> float:
    token = str(raw or "").strip().upper()
    if not token:
        return 0.0
    if token in ATTENDANCE_PRESENT or token in ATTENDANCE_OT_DAY:
        return 1.0
    if token in ATTENDANCE_HALF:
        return 0.5
    return 0.0


def count_total_days(attendance: dict | None) -> float:
    if not isinstance(attendance, dict):
        return 0.0
    return round(sum(_day_value_points(value) for value in attendance.values()), 1)


def parse_money(value: object) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(round(float(str(value).replace(",", "").strip())))
    except (TypeError, ValueError):
        return 0


def parse_ot_amount(value: object) -> int:
    return parse_money(value)


def final_payment(
    total_days: float,
    wage: int,
    ot_amount: int,
    advance: int,
    food: int | None = None,
) -> int:
    """(Total Days × Wage) + OT - Advance - Food"""
    base = round(total_days * (wage or 0))
    food_amount = food or 0
    return max(0, base + (ot_amount or 0) - (advance or 0) - food_amount)


def next_attendance_code(current: str | None) -> str:
    """Cycle: empty → P → A → H → OT → empty."""
    token = str(current or "").strip().upper()
    order = ["", "P", "A", "H", "OT"]
    if token == "1":
        token = "P"
    try:
        idx = order.index(token)
    except ValueError:
        idx = 0
    nxt = order[(idx + 1) % len(order)]
    return nxt
