from __future__ import annotations

import math

from schemas.feature_graph import FeatureGraph
from schemas.projection_graph import ProjectionGraph
from parser.projection_mapping import internal_to_front


def validate(input_graph: ProjectionGraph, features: FeatureGraph, backend: dict, tolerance_mm: float = 0.01) -> dict:
    """v0.1 compares structured projection invariants; it does not yet extract drawing linework."""
    base = features.base_block
    total_depth = base.depth + sum(b.depth for b in features.bosses)
    generated = {"front": (base.width, base.height), "top": (base.width, total_depth), "left": (total_depth, base.height)}
    expected = {"front": (input_graph.front.horizontal_extent, input_graph.front.vertical_extent), "top": (input_graph.top.horizontal_extent, input_graph.top.vertical_extent), "left": (input_graph.left.horizontal_extent, input_graph.left.vertical_extent)}
    checks = [{"view": view, "passed": all(abs(a-b) <= tolerance_mm for a, b in zip(generated[view], expected[view])), "expected_mm": expected[view], "generated_mm": generated[view]} for view in expected]
    hole_checks = []
    for hole, circle in zip(features.holes, input_graph.front.circles):
        x, y = internal_to_front(hole.center_x, hole.center_y, base.width, base.height)
        hole_checks.append({"diameter_mm": hole.diameter, "position_mm": [x, y], "passed": abs(hole.diameter-circle.diameter) <= tolerance_mm and abs(x-circle.x) <= tolerance_mm and abs(y-circle.y) <= tolerance_mm})
    slot_checks = []
    declared = (input_graph.feature_evidence or {}).get("straight_slot", {}).get("expected", {})
    for slot in features.slots:
        x, y = internal_to_front(slot.center_x_mm, slot.center_y_mm, base.width, base.height)
        candidates = backend.get("geometry", {}).get("slot_arc_candidates", [])
        measured_center = ([sum(float(face.get("position_mm", [0,0])[index]) for face in candidates[:2])/2 for index in (0,1)] if len(candidates) >= 2 else None)
        center_error = math.dist(measured_center, [slot.center_x_mm, slot.center_y_mm]) if measured_center else None
        slot_checks.append({"type": slot.type, "overall_length_mm": slot.overall_length_mm,
                            "width_mm": slot.width_mm, "position_mm": [x, y],
                            "passed": abs(slot.overall_length_mm-float(declared.get("overall_length_mm", slot.overall_length_mm))) <= tolerance_mm
                                      and abs(slot.width_mm-float(declared.get("width_mm", slot.width_mm))) <= tolerance_mm
                                      and all(abs(a-b) <= tolerance_mm for a,b in zip((x,y), declared.get("center_mm", [x,y])))
                                      and center_error is not None and center_error <= tolerance_mm,
                            "expected_model_center_mm": [slot.center_x_mm, slot.center_y_mm],
                            "measured_model_center_mm": measured_center, "center_error_mm": center_error})
    drawing = backend.get("drawing_structure", {})
    drawing_check = {"id": "regenerated_drawing_has_three_views", "passed": backend.get("drawing_create", {}).get("status") == "pass" and drawing.get("view_count") == 3}
    return {"status": "PASS" if all(c["passed"] for c in checks+hole_checks+slot_checks+[drawing_check]) else "FAIL", "mode": "structured_projection_invariants_plus_generated_drawing_structure", "limitations": ["Level 1 is structured; Level 2 performs drawing primitive comparison"], "view_checks": checks, "hole_checks": hole_checks, "slot_checks": slot_checks, "drawing_check": drawing_check}
