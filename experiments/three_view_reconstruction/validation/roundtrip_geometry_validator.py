from __future__ import annotations
from validation.primitive_matcher import match


def validate(graph, extracted: dict) -> dict:
    if extracted.get("status") != "PARTIAL":
        return {"status": "FAIL", "reason": "drawing extraction failed", "extraction": extracted}
    # Standard-view generation returns front/top/right in this order.  The
    # contract maps right to the input's left orthographic axis.
    expected_views = (graph.front, graph.top, graph.left)
    reports = {}
    for key, expected, actual in zip(("front", "top", "left"), expected_views, extracted["views"]):
        visible = match([x.__dict__ for x in expected.visible_segments], actual["visible_segments"], "line")
        circles = match([x.__dict__ for x in expected.circles], actual["circles"], "circle")
        reports[key] = {"visible_lines": visible, "hidden_lines": {"status": "NOT_EVALUABLE", "expected": len(expected.hidden_segments), "reason": "SW2024 API response did not expose visibility semantics"}, "circles": circles, "arcs": {"status": "NOT_EVALUABLE", "expected": len(expected.arcs)}, "centerlines": {"status": "NOT_EVALUABLE", "expected": len(expected.centerlines)}}
    return {"status": "PARTIAL", "overall_rule": "cannot PASS while requested hidden-line semantics are not extractable", "views": reports, "extraction": {"api": extracted["api"], "coordinate_space": extracted["coordinate_space"], "capability_gap": extracted["capability_gap"]}}
