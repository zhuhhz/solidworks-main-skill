from __future__ import annotations

from schemas.projection_graph import ProjectionGraph
from parser.projection_mapping import validate_projection_name


def validate(graph: ProjectionGraph, tolerance_mm: float = 0.01) -> dict:
    validate_projection_name(graph.projection)
    checks = [
        ("front.width_equals_top.width", graph.front.horizontal_extent, graph.top.horizontal_extent),
        ("front.height_equals_left.height", graph.front.vertical_extent, graph.left.vertical_extent),
        ("top.depth_equals_left.depth", graph.top.vertical_extent, graph.left.horizontal_extent),
    ]
    results = [{"id": key, "expected_mm": a, "actual_mm": b, "passed": abs(a-b) <= tolerance_mm} for key, a, b in checks]
    return {"status": "PASS" if all(x["passed"] for x in results) else "FAIL", "tolerance_mm": tolerance_mm, "checks": results,
            "error_code": None if all(x["passed"] for x in results) else "INPUT_INCONSISTENT"}
