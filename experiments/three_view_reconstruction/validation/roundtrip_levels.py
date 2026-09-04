"""Explicit Level 2A geometry and Level 2B semantic result contracts."""
from __future__ import annotations


def split(level_2: dict, semantic_graph: dict | None = None) -> dict:
    views = level_2.get("views", {})
    geometry_complete = bool(views) and all(
        v.get("visible_lines", {}).get("recall") == 1.0
        and v.get("circles", {}).get("recall") == 1.0
        for v in views.values()
    )
    level_2a = {"status": "PASS" if geometry_complete else "PARTIAL", "scope": "lines/circles/arcs only; semantics excluded", "views": views}
    annotations = sum(1 for v in (semantic_graph or {}).get("views", []) for p in v.get("primitives", []) if p.get("semantic") == "CENTERMARK")
    level_2b = {"status": "PARTIAL", "scope": "visible/hidden/centerline/centermark semantics", "known_center_marks": annotations, "reason": "No exact hidden/visible projected-primitive provenance has been demonstrated."}
    return {"level_2a_vector_geometry": level_2a, "level_2b_drawing_semantics": level_2b}
