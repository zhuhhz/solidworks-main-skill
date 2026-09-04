"""Merge projected primitives and annotation evidence without guessing semantics."""
from __future__ import annotations


SEMANTICS = {"VISIBLE", "HIDDEN", "CENTERLINE", "CENTERMARK", "UNKNOWN"}


def extract(projected: dict, drawing_structure: dict | None = None) -> dict:
    drawing_structure = drawing_structure or {}
    annotations = drawing_structure.get("professional_annotations", {})
    marks = annotations.get("center_marks", [])
    views = []
    for view in projected.get("views", []):
        primitives = []
        primitives += [{"geometry_type": "LINE", "semantic": "UNKNOWN", "source": "IView.GetPolyLinesAndCurves", "confidence": 0.0, "geometry": x} for x in view.get("visible_segments", [])]
        primitives += [{"geometry_type": "CIRCLE", "semantic": "UNKNOWN", "source": "IView.GetPolyLinesAndCurves", "confidence": 0.0, "geometry": x} for x in view.get("circles", [])]
        owner_marks = [m for m in marks if m.get("view") == view.get("name")]
        primitives += [{"geometry_type": "ANNOTATION", "semantic": "CENTERMARK", "source": "DrawingAnnotation", "confidence": 1.0, "geometry": {"size_m": m.get("size_m"), "show_lines": m.get("show_lines")}} for m in owner_marks]
        views.append({"name": view.get("name"), "semantic_view": view.get("semantic_view"), "orientation": view.get("orientation"), "primitives": primitives})
    return {"status": "PARTIAL", "views": views, "limitations": ["Projected primitive visibility is UNKNOWN until API/topology evidence is demonstrated.", "Center marks are read independently as annotation evidence."]}
