from __future__ import annotations
from drawing.view_orientation import CanonicalViewOrientation, canonicalize
from parser.projection_mapping import map_arcs_to_frame, map_circles_to_frame, map_lines_to_frame
from validation.primitive_matcher import match


def _implicit_outline(view) -> list[dict]:
    """The structured schema permits an outer rectangle by extents alone."""
    if view.visible_segments:
        return [x.__dict__ for x in view.visible_segments]
    width, height = view.horizontal_extent, view.vertical_extent
    return [
        {"x1": 0, "y1": 0, "x2": width, "y2": 0},
        {"x1": width, "y1": 0, "x2": width, "y2": height},
        {"x1": width, "y1": height, "x2": 0, "y2": height},
        {"x1": 0, "y1": height, "x2": 0, "y2": 0},
    ]


def validate(graph, extracted: dict) -> dict:
    if extracted.get("status") != "PARTIAL":
        return {"status": "FAIL", "reason": "drawing extraction failed", "extraction": extracted}
    # Select by canonical frame, never by localized name or sheet order. The
    # current third-angle drawing contract represents the input Left axes with
    # a generated Right view and an explicit frame transform.
    actual_by_role = {}
    for actual in extracted["views"]:
        role = actual.get("orientation", {}).get("canonical_role")
        if role:
            actual_by_role[role] = actual
    expected_views = (("front", graph.front, CanonicalViewOrientation.FRONT),
                      ("top", graph.top, CanonicalViewOrientation.TOP),
                      ("left", graph.left, CanonicalViewOrientation.RIGHT))
    reports = {}
    for key, expected, target_role in expected_views:
        actual = actual_by_role.get(target_role.value)
        if actual is None:
            reports[key] = {"status": "FAIL", "reason": f"canonical view {target_role.value} missing"}
            continue
        target_frame = canonicalize(target_role.value, graph.projection.upper())
        expected_lines = map_lines_to_frame(key, _implicit_outline(expected), expected.horizontal_extent, expected.vertical_extent, target_frame)
        expected_circles = map_circles_to_frame(key, [x.__dict__ for x in expected.circles], expected.horizontal_extent, expected.vertical_extent, target_frame)
        expected_arcs = map_arcs_to_frame(key, [x.__dict__ for x in expected.arcs], expected.horizontal_extent, expected.vertical_extent, target_frame)
        visible = match(expected_lines, actual["visible_segments"], "line")
        circles = match(expected_circles, actual["circles"], "circle")
        arcs = match(expected_arcs, actual["arcs"], "arc")
        reports[key] = {"visible_lines": visible, "hidden_lines": {"status": "NOT_EVALUABLE", "expected": len(expected.hidden_segments), "reason": "SW2024 API response did not expose visibility semantics"}, "circles": circles, "arcs": arcs, "centerlines": {"status": "NOT_EVALUABLE", "expected": len(expected.centerlines)}}
    return {"status": "PARTIAL", "overall_rule": "cannot PASS while requested hidden-line semantics are not extractable", "views": reports, "extraction": {"api": extracted["api"], "coordinate_space": extracted["coordinate_space"], "capability_gap": extracted["capability_gap"]}}
