"""Explicit SolidWorks projected-coordinate to stable view-local-mm transform."""
from __future__ import annotations
from copy import deepcopy


def to_view_local_mm(point_m: tuple[float, float], *, scale: float) -> tuple[float, float]:
    """Convert SW2024 projected coordinates to model-mm coordinates.

    The B001 SW2024 probe proved ``IView.GetPolyLinesAndCurves`` returns model
    lengths in metres (a 100 mm edge is 0.100), even when the sheet view scale
    is 1:2.  ``scale`` remains recorded for diagnostics but must not be
    applied a second time.
    """
    if scale <= 0:
        raise ValueError("view scale must be positive")
    return (point_m[0] * 1000.0, point_m[1] * 1000.0)


def transform_metadata(scale: float) -> dict:
    return {"source_units": "SolidWorks projected model metres", "target_units": "view-local model mm", "translation_removed": "bounding-box origin normalized by extractor", "view_scale_recorded": scale, "scale_removed": False, "axis_flip": False}


def normalize_primitives(lines: list[dict], circles: list[dict]) -> tuple[list[dict], list[dict], tuple[float, float]]:
    """Remove sheet translation without applying view scale a second time."""
    normalized_lines, normalized_circles = deepcopy(lines), deepcopy(circles)
    xs = [p[k] for p in normalized_lines for k in ("x1", "x2")]
    ys = [p[k] for p in normalized_lines for k in ("y1", "y2")]
    xs += [c["x"] - c["diameter"] / 2 for c in normalized_circles]
    ys += [c["y"] - c["diameter"] / 2 for c in normalized_circles]
    dx, dy = (min(xs), min(ys)) if xs and ys else (0.0, 0.0)
    for line in normalized_lines:
        line["x1"] -= dx; line["x2"] -= dx
        line["y1"] -= dy; line["y2"] -= dy
    for circle in normalized_circles:
        circle["x"] -= dx; circle["y"] -= dy
    return normalized_lines, normalized_circles, (dx, dy)
