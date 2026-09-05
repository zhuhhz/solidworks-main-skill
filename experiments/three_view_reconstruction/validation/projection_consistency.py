from __future__ import annotations

from schemas.projection_graph import ProjectionGraph
from parser.projection_mapping import validate_projection_name
from inference.slot_inference import analyze_slot_contract
from inference.evidence_binding import build_feature_graph_from_evidence


def validate(graph: ProjectionGraph, tolerance_mm: float = 0.01) -> dict:
    validate_projection_name(graph.projection)
    checks = [
        ("front.width_equals_top.width", graph.front.horizontal_extent, graph.top.horizontal_extent),
        ("front.height_equals_left.height", graph.front.vertical_extent, graph.left.vertical_extent),
        ("top.depth_equals_left.depth", graph.top.vertical_extent, graph.left.horizontal_extent),
    ]
    results = [{"id": key, "expected_mm": a, "actual_mm": b, "passed": abs(a-b) <= tolerance_mm} for key, a, b in checks]
    slot = analyze_slot_contract(graph) if not graph.feature_evidence_records else {"status": "NOT_APPLICABLE"}
    evidence = None
    if graph.feature_evidence_records:
        _, evidence = build_feature_graph_from_evidence(graph)
    dimensions_pass = all(x["passed"] for x in results)
    passed = (dimensions_pass and slot.get("status") != "FAIL"
              and (evidence is None or evidence["status"] == "PASS"))
    error_code = None
    if not passed:
        error_code = (evidence or {}).get("error_code") if dimensions_pass and slot.get("status") != "FAIL" else "INPUT_INCONSISTENT"
    return {"status": "PASS" if passed else "FAIL", "tolerance_mm": tolerance_mm, "checks": results,
            "slot_contract": {k: v for k, v in slot.items() if k != "slot"},
            "feature_evidence_consistency": evidence,
            "error_code": error_code}
