"""Single source of truth for orthographic coordinate correspondences."""
from __future__ import annotations


def validate_projection_name(projection: str) -> str:
    if projection not in {"first_angle", "third_angle"}:
        raise ValueError("projection 必须是 first_angle 或 third_angle")
    return projection


def front_to_internal(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> tuple[float, float]:
    """Input front-view lower-left coordinate -> model-centred X/Y."""
    return x_mm - width_mm / 2.0, y_mm - height_mm / 2.0


def internal_to_front(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> tuple[float, float]:
    return x_mm + width_mm / 2.0, y_mm + height_mm / 2.0


def correspondences() -> dict[str, str]:
    return {"front.x": "top.x", "front.y": "left.y", "top.z": "left.z"}
