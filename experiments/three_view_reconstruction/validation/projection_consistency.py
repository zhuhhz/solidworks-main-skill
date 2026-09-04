from __future__ import annotations

from schemas.projection_graph import ProjectionGraph
from parser.projection_mapping import validate_projection_name
from inference.slot_inference import analyze_slot_contract


def validate(graph: ProjectionGraph, tolerance_mm: float = 0.01) -> dict:
    validate_projection_name(graph.projection)
    checks = [
        ("front.width_equals_top.width", graph.front.horizontal_extent, graph.top.horizontal_extent),
        ("front.height_equals_left.height", graph.front.vertical_extent, graph.left.vertical_extent),
        ("top.depth_equals_left.depth", graph.top.vertical_extent, graph.left.horizontal_extent),
    ]
    results = [{"id": key, "expected_mm": a, "actual_mm": b, "passed": abs(a-b) <= tolerance_mm} for key, a, b in checks]
    slot = analyze_slot_contract(graph)
    passed = all(x["passed"] for x in results) and slot.get("status") != "FAIL"
    return {"status": "PASS" if passed else "FAIL", "tolerance_mm": tolerance_mm, "checks": results,
            "slot_contract": {k: v for k, v in slot.items() if k != "slot"},
            "error_code": None if passed else "INPUT_INCONSISTENT"}
