from calendar import monthrange
from datetime import date

from backend.services.attendance import (
    calc_ot_amount,
    count_total_days,
    count_total_ot_hours,
    final_payment,
    parse_ot_rate,
)

__all__ = [
    "days_in_month",
    "weekday_labels",
    "count_total_days",
    "count_total_ot_hours",
    "parse_ot_rate",
    "calc_ot_amount",
    "parse_money",
    "parse_ot_amount",
    "final_payment",
]


def days_in_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def weekday_labels(year: int, month: int) -> list[str]:
    count = days_in_month(year, month)
    return [date(year, month, day).strftime("%a") for day in range(1, count + 1)]


def parse_money(value: object) -> int:
    return parse_ot_rate(value)


def parse_ot_amount(value: object) -> int:
    """Legacy: when ot column held total amount. Prefer computed OT from attendance."""
    return parse_ot_rate(value)


def next_attendance_code(current: str | None) -> str:
    """Cycle: empty → P → A → H → P+OT → empty (legacy string API)."""
    from backend.services.attendance import parse_day_entry

    status, _ = parse_day_entry(current)
    order = ["", "P", "A", "H", "P+OT"]
    try:
        idx = order.index(status)
    except ValueError:
        idx = 0
    return order[(idx + 1) % len(order)]
