"""Explicit Level 2A geometry and Level 2B semantic result contracts."""
from __future__ import annotations


def split(level_2: dict, semantic_graph: dict | None = None, expected_graph=None) -> dict:
    views = level_2.get("views", {})
    geometry_complete = bool(views) and all(
        v.get("visible_lines", {}).get("status") == "PASS"
        and v.get("circles", {}).get("status") == "PASS"
        for v in views.values()
    )
    level_2a = {"status": "PASS" if geometry_complete else "PARTIAL", "scope": "lines/circles/arcs only; semantics excluded", "views": views}
    semantic_graph = semantic_graph or {}
    known_center_marks = len(semantic_graph.get("annotations", {}).get("center_marks", []))
    actual_center_lines = len(semantic_graph.get("annotations", {}).get("center_lines", []))
    requirements = list(getattr(expected_graph, "center_requirements", None) or []) if expected_graph else []
    expected_center_marks = sum(int(item.get("count", 1)) for item in requirements if item.get("kind") == "CENTERMARK")
    required_annotation_center_lines = sum(int(item.get("count", 1)) for item in requirements if item.get("kind") == "CENTERLINE")
    expected_center_lines = (sum(len(view.centerlines) for view in (expected_graph.front, expected_graph.top, expected_graph.left)) if expected_graph else 0) + required_annotation_center_lines
    hidden_count = sum(len(v.get("projected_geometry", {}).get("hidden", [])) for v in semantic_graph.get("views", []))
    unknown_count = semantic_graph.get("unknown_projected_primitive_count", 0)
    provenance_ok = semantic_graph.get("status") == "PASS" and semantic_graph.get("semantic_provenance") == "HLV_MINUS_HLR" and unknown_count == 0
    centerline_complete = actual_center_lines >= expected_center_lines
    centermark_complete = known_center_marks >= expected_center_marks
    level_2b_status = "PASS" if provenance_ok and centerline_complete and centermark_complete else "PARTIAL"
    reasons = []
    if not provenance_ok: reasons.append("SEMANTIC_PROVENANCE_UNAVAILABLE")
    if not centerline_complete: reasons.append("EXPECTED_CENTERLINE_ANNOTATIONS_MISSING")
    if not centermark_complete: reasons.append("EXPECTED_CENTERMARK_ANNOTATIONS_MISSING")
    level_2b = {"status": level_2b_status, "scope": "visible/hidden/centerline/centermark semantics",
                "semantic_provenance": semantic_graph.get("semantic_provenance"),
                "hidden_primitive_count": hidden_count, "unknown_primitive_count": unknown_count,
                "known_center_marks": known_center_marks, "expected_center_marks": expected_center_marks,
                "expected_center_lines": expected_center_lines,
                "actual_center_lines": actual_center_lines, "reasons": reasons}
    return {"level_2a_vector_geometry": level_2a, "level_2b_drawing_semantics": level_2b}
