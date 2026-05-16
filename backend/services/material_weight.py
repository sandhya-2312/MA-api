"""Steel material weight (kg) from mm dimensions — matches frontend engineering formulas."""

from __future__ import annotations

import math
import re
from typing import Any

STEEL_DENSITY_KG_M3 = 7850.0
MM_PER_M = 1000.0


def _parse_positive_mm(value: object) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    match = re.search(r"[\d.]+", raw)
    if not match:
        return None
    try:
        num = float(match.group())
    except ValueError:
        return None
    if not math.isfinite(num) or num <= 0:
        return None
    return num


def parse_dimension_parts(raw: str) -> list[float]:
    if not raw or not str(raw).strip():
        return []
    parts: list[float] = []
    for match in re.finditer(r"[\d.]+", str(raw)):
        try:
            num = float(match.group())
        except ValueError:
            continue
        if math.isfinite(num) and num > 0:
            parts.append(num)
    return parts


def normalize_material_type(name: str) -> str:
    n = (name or "").strip().lower()
    if "angle" in n or "angel" in n:
        return "MS Angle"
    if "rod" in n:
        return "MS Rod"
    if "pipe" in n:
        return "MS Pipe"
    if "flange" in n or "flunge" in n:
        return "MS Flange"
    if "flat" in n:
        return "MS Flat Bar"
    if "plate" in n:
        return "MS Plate"
    return "Add manually"


def _mm_to_m(mm: float) -> float:
    return mm / MM_PER_M


def compute_weight_kg(
    material_type: str,
    *,
    length_mm: float | None = None,
    width_mm: float | None = None,
    thickness_mm: float | None = None,
    diameter_mm: float | None = None,
    outer_diameter_mm: float | None = None,
    inner_diameter_mm: float | None = None,
    side_a_mm: float | None = None,
    side_b_mm: float | None = None,
    quantity: float = 1.0,
) -> float:
    """Volume (m³) × 7850 × qty — formulas per material type."""
    qty = max(quantity, 1.0)
    pi = math.pi
    density = STEEL_DENSITY_KG_M3
    volume_m3 = 0.0

    if material_type == "MS Plate":
        if length_mm and width_mm and thickness_mm:
            volume_m3 = _mm_to_m(length_mm) * _mm_to_m(width_mm) * _mm_to_m(thickness_mm)
    elif material_type == "MS Rod":
        if diameter_mm and length_mm:
            r = _mm_to_m(diameter_mm) / 2
            volume_m3 = pi * r * r * _mm_to_m(length_mm)
    elif material_type == "MS Pipe":
        if outer_diameter_mm and inner_diameter_mm is not None and length_mm:
            od = _mm_to_m(outer_diameter_mm)
            id_ = _mm_to_m(inner_diameter_mm)
            if od > id_:
                volume_m3 = pi * ((od * od - id_ * id_) / 4) * _mm_to_m(length_mm)
    elif material_type == "MS Flat Bar":
        if width_mm and thickness_mm and length_mm:
            volume_m3 = _mm_to_m(width_mm) * _mm_to_m(thickness_mm) * _mm_to_m(length_mm)
    elif material_type == "MS Angle":
        if side_a_mm and side_b_mm and thickness_mm and length_mm:
            a, b, t, l = map(_mm_to_m, (side_a_mm, side_b_mm, thickness_mm, length_mm))
            if a + b > t:
                volume_m3 = (a + b - t) * t * l
    elif material_type == "MS Flange":
        if outer_diameter_mm and inner_diameter_mm is not None and thickness_mm:
            od = _mm_to_m(outer_diameter_mm)
            id_ = _mm_to_m(inner_diameter_mm)
            if od > id_:
                volume_m3 = pi * ((od * od - id_ * id_) / 4) * _mm_to_m(thickness_mm)
    elif material_type == "Add manually":
        if length_mm and width_mm and thickness_mm:
            volume_m3 = _mm_to_m(length_mm) * _mm_to_m(width_mm) * _mm_to_m(thickness_mm)

    if volume_m3 <= 0:
        return 0.0
    return volume_m3 * density * qty


def _dims_from_meta(meta: dict[str, Any]) -> tuple[str, list[float]]:
    name = str(meta.get("itemDetails") or meta.get("item_details") or "").strip()
    stored = str(meta.get("dimensions") or "").strip()
    if stored:
        return name, parse_dimension_parts(stored)
    parts: list[float] = []
    for key in ("lengthMm", "widthMm", "thkDia", "barLengthMm"):
        v = _parse_positive_mm(meta.get(key))
        if v is not None:
            parts.append(v)
    return name, parts


def _fields_from_dimensions(material_type: str, dims: list[float]) -> dict[str, float | None]:
    f: dict[str, float | None] = {
        "length_mm": None,
        "width_mm": None,
        "thickness_mm": None,
        "diameter_mm": None,
        "outer_diameter_mm": None,
        "inner_diameter_mm": None,
        "side_a_mm": None,
        "side_b_mm": None,
    }
    if material_type == "MS Plate" and len(dims) >= 3:
        f["length_mm"], f["width_mm"], f["thickness_mm"] = dims[0], dims[1], dims[2]
    elif material_type == "MS Rod" and len(dims) >= 2:
        f["diameter_mm"], f["length_mm"] = dims[0], dims[1]
    elif material_type == "MS Pipe" and len(dims) >= 3:
        f["outer_diameter_mm"], f["inner_diameter_mm"], f["length_mm"] = dims[0], dims[1], dims[2]
    elif material_type == "MS Flat Bar" and len(dims) >= 3:
        f["width_mm"], f["thickness_mm"], f["length_mm"] = dims[0], dims[1], dims[2]
    elif material_type == "MS Angle" and len(dims) >= 4:
        f["side_a_mm"], f["side_b_mm"], f["thickness_mm"], f["length_mm"] = dims[0], dims[1], dims[2], dims[3]
    elif material_type == "MS Angle" and len(dims) >= 3:
        f["side_a_mm"], f["side_b_mm"], f["thickness_mm"] = dims[0], dims[1], dims[2]
    elif material_type == "MS Flange" and len(dims) >= 3:
        f["outer_diameter_mm"], f["inner_diameter_mm"], f["thickness_mm"] = dims[0], dims[1], dims[2]
    elif material_type == "Add manually" and len(dims) >= 3:
        f["length_mm"], f["width_mm"], f["thickness_mm"] = dims[0], dims[1], dims[2]
    return f


def validate_material_fields(
    material_type: str,
    *,
    length_mm: float | None = None,
    width_mm: float | None = None,
    thickness_mm: float | None = None,
    diameter_mm: float | None = None,
    outer_diameter_mm: float | None = None,
    inner_diameter_mm: float | None = None,
    side_a_mm: float | None = None,
    side_b_mm: float | None = None,
    quantity: float = 1.0,
) -> tuple[float, list[str]]:
    """Return (weight_kg, errors)."""
    errors: list[str] = []
    if quantity <= 0:
        errors.append("Quantity must be a positive number.")

    if material_type == "MS Plate":
        for label, val in (("Length", length_mm), ("Width", width_mm), ("Thickness", thickness_mm)):
            if val is None:
                errors.append(f"{label} (mm) must be a positive number.")
    elif material_type == "MS Rod":
        if diameter_mm is None:
            errors.append("Diameter (mm) must be a positive number.")
        if length_mm is None:
            errors.append("Length (mm) must be a positive number.")
    elif material_type == "MS Pipe":
        if outer_diameter_mm is None:
            errors.append("Outer diameter (mm) must be a positive number.")
        if inner_diameter_mm is None:
            errors.append("Inner diameter (mm) must be a positive number.")
        elif outer_diameter_mm is not None and inner_diameter_mm >= outer_diameter_mm:
            errors.append("Outer diameter must be greater than inner diameter.")
        if length_mm is None:
            errors.append("Length (mm) must be a positive number.")
    elif material_type == "MS Flat Bar":
        for label, val in (("Width", width_mm), ("Thickness", thickness_mm), ("Length", length_mm)):
            if val is None:
                errors.append(f"{label} (mm) must be a positive number.")
    elif material_type == "MS Angle":
        for label, val in (
            ("Leg A", side_a_mm),
            ("Leg B", side_b_mm),
            ("Thickness", thickness_mm),
            ("Bar length", length_mm),
        ):
            if val is None:
                errors.append(f"{label} (mm) must be a positive number.")
        if (
            side_a_mm is not None
            and side_b_mm is not None
            and thickness_mm is not None
            and side_a_mm + side_b_mm <= thickness_mm
        ):
            errors.append("Leg A + Leg B must be greater than thickness.")
    elif material_type == "MS Flange":
        if outer_diameter_mm is None:
            errors.append("Outer diameter (mm) must be a positive number.")
        if inner_diameter_mm is None:
            errors.append("Inner diameter (mm) must be a positive number.")
        elif outer_diameter_mm is not None and inner_diameter_mm >= outer_diameter_mm:
            errors.append("Outer diameter must be greater than inner diameter.")
        if thickness_mm is None:
            errors.append("Thickness (mm) must be a positive number.")
    elif material_type == "Add manually":
        for label, val in (("Length", length_mm), ("Width", width_mm), ("Thickness", thickness_mm)):
            if val is None:
                errors.append(f"{label} (mm) must be a positive number.")
    else:
        errors.append(f"Unknown material type: {material_type}")

    weight = compute_weight_kg(
        material_type,
        length_mm=length_mm,
        width_mm=width_mm,
        thickness_mm=thickness_mm,
        diameter_mm=diameter_mm,
        outer_diameter_mm=outer_diameter_mm,
        inner_diameter_mm=inner_diameter_mm,
        side_a_mm=side_a_mm,
        side_b_mm=side_b_mm,
        quantity=quantity,
    )
    if not errors and weight <= 0:
        errors.append("Calculated weight is invalid. Check dimensions and material type.")
    return round(weight, 4), errors


def validate_entry_meta(meta: dict[str, Any] | None) -> tuple[float, list[str]]:
    """Validate a project data entry meta dict; return (weight_kg, errors)."""
    if not meta or not isinstance(meta, dict):
        return 0.0, ["Entry metadata is required for weight validation."]
    name, dims = _dims_from_meta(meta)
    if not name:
        return 0.0, ["Material name (itemDetails) is required."]
    material_type = normalize_material_type(name)
    qty_raw = meta.get("qty") or meta.get("quantity") or "1"
    qty = _parse_positive_mm(qty_raw) or 0.0
    fields = _fields_from_dimensions(material_type, dims)
    # MS Angle: merge bar length from meta when dimensions only have 3 parts
    if material_type == "MS Angle" and fields.get("length_mm") is None:
        bar = _parse_positive_mm(meta.get("barLengthMm"))
        if bar is not None:
            fields["length_mm"] = bar
    # Fallback: map legacy lengthMm/widthMm/thkDia for angles (A, B, T)
    if material_type == "MS Angle":
        if fields.get("side_a_mm") is None:
            fields["side_a_mm"] = _parse_positive_mm(meta.get("lengthMm"))
        if fields.get("side_b_mm") is None:
            fields["side_b_mm"] = _parse_positive_mm(meta.get("widthMm"))
        if fields.get("thickness_mm") is None:
            fields["thickness_mm"] = _parse_positive_mm(meta.get("thkDia"))
        if fields.get("length_mm") is None:
            fields["length_mm"] = _parse_positive_mm(meta.get("barLengthMm"))
    return validate_material_fields(material_type, quantity=qty, **fields)


def validate_initial_item(item: Any) -> tuple[float, list[str]]:
    """Validate InitialProjectItem-like object (attributes or dict)."""

    def _get(key: str, snake: str) -> str:
        if isinstance(item, dict):
            return str(item.get(key) or item.get(snake) or "")
        return str(getattr(item, snake, None) or getattr(item, key, None) or "")

    name = _get("itemDetails", "item_details").strip() or _get("item_details", "item_details").strip()
    if not name:
        return 0.0, ["Material name (item_details) is required."]
    material_type = normalize_material_type(name)
    dims = parse_dimension_parts(_get("dimensions", "dimensions"))
    if not dims:
        l = _parse_positive_mm(_get("lengthMm", "length_mm"))
        w = _parse_positive_mm(_get("widthMm", "width_mm"))
        t = _parse_positive_mm(_get("thkDia", "thk_dia"))
        bar = _parse_positive_mm(_get("barLengthMm", "bar_length_mm"))
        if material_type == "MS Angle" and l and w and t:
            dims = [l, w, t] + ([bar] if bar else [])
        elif l and w and t:
            dims = [l, w, t]
    fields = _fields_from_dimensions(material_type, dims)
    qty = _parse_positive_mm(_get("qty", "qty")) or 1.0
    weight, errors = validate_material_fields(material_type, quantity=qty, **fields)
    explicit = _get("weightKg", "weight_kg").strip() or _get("weight_kg", "weight_kg").strip()
    if explicit and not errors:
        explicit_w = _parse_positive_mm(explicit)
        if explicit_w is not None and abs(explicit_w - weight) > 0.05:
            errors.append("Provided weight does not match calculated weight from dimensions.")
    return weight, errors
