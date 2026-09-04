"""Explicit SolidWorks projected-coordinate to stable view-local-mm transform."""
from __future__ import annotations


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
