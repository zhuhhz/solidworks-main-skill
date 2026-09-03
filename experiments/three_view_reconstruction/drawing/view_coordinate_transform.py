"""Explicit sheet-metre to stable view-local-mm transformation."""
from __future__ import annotations


def to_view_local_mm(point_m: tuple[float, float], *, scale: float) -> tuple[float, float]:
    """GetPolyLinesAndCurves coordinates are already view-centred; remove scale."""
    if scale <= 0:
        raise ValueError("view scale must be positive")
    return (point_m[0] * 1000.0 / scale, point_m[1] * 1000.0 / scale)


def transform_metadata(scale: float) -> dict:
    return {"source_units": "drawing metres", "target_units": "view-local mm", "translation_removed": "API returns view-local coordinates", "scale_removed": scale, "axis_flip": False}
