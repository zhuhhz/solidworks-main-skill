"""Evidence-driven inference for Benchmark 003 straight through slots."""
from __future__ import annotations

import math
from schemas.feature_graph import FeatureHypothesis, StraightSlot
from parser.projection_mapping import front_to_internal

TOLERANCE_MM = 0.01
ANGLE_TOLERANCE_DEG = 0.1


def _point(arc, angle):
    value = math.radians(angle)
    return (arc.x + arc.radius * math.cos(value), arc.y + arc.radius * math.sin(value))


def _near(a, b, tol=TOLERANCE_MM):
    return math.dist(a, b) <= tol


def analyze_slot_contract(graph) -> dict:
    lines, arcs = graph.front.visible_segments, graph.front.arcs
    # Remove the four base-outline segments by retaining only non-boundary lines.
    w, h = graph.front.horizontal_extent, graph.front.vertical_extent
    inner = [line for line in lines if not (
        (abs(line.y1-line.y2) <= TOLERANCE_MM and (abs(line.y1) <= TOLERANCE_MM or abs(line.y1-h) <= TOLERANCE_MM)) or
        (abs(line.x1-line.x2) <= TOLERANCE_MM and (abs(line.x1) <= TOLERANCE_MM or abs(line.x1-w) <= TOLERANCE_MM))
    )]
    if not arcs and not (graph.feature_evidence or {}).get("straight_slot"):
        return {"status": "NONE"}
    failures = []
    if len(inner) != 2 or len(arcs) != 2:
        failures.append("closed contour requires exactly two inner lines and two arcs")
    if failures:
        return {"status": "FAIL", "error_code": "INPUT_INCONSISTENT", "contradictions": failures}
    horizontal = all(abs(line.y2-line.y1) <= TOLERANCE_MM for line in inner)
    vertical = all(abs(line.x2-line.x1) <= TOLERANCE_MM for line in inner)
    if not (horizontal or vertical): failures.append("slot lines are not parallel to a principal axis")
    major_axis = "X" if horizontal else "Y"
    if abs(arcs[0].radius-arcs[1].radius) > TOLERANCE_MM: failures.append("end arc radii differ")
    if any(abs(arc.sweep_deg-180.0) > ANGLE_TOLERANCE_DEG for arc in arcs): failures.append("straight slot end arcs must be semicircles")
    radius = sum(a.radius for a in arcs) / 2
    if horizontal:
        separation = abs((inner[0].y1+inner[0].y2)/2-(inner[1].y1+inner[1].y2)/2)
        centres_aligned = abs(arcs[0].y-arcs[1].y) <= TOLERANCE_MM
        centre_distance = abs(arcs[0].x-arcs[1].x)
    else:
        separation = abs(inner[0].x1-inner[1].x1)
        centres_aligned = abs(arcs[0].x-arcs[1].x) <= TOLERANCE_MM
        centre_distance = abs(arcs[0].y-arcs[1].y)
    if not centres_aligned: failures.append("end arc centres are not axis-aligned")
    if abs(separation-2*radius) > TOLERANCE_MM: failures.append("line spacing and slot width conflict")
    # Each line endpoint must lie on an arc endpoint. This simultaneously proves closure.
    arc_endpoints = [_point(a, a.start_angle_deg) for a in arcs] + [_point(a, a.end_angle_deg) for a in arcs]
    endpoints = [(line.x1, line.y1) for line in inner] + [(line.x2, line.y2) for line in inner]
    if not all(any(_near(point, target) for target in arc_endpoints) for point in endpoints):
        failures.append("line/arc contour is open")
    # Radius at a line junction must be perpendicular to the line direction.
    for line in inner:
        direction = (line.x2-line.x1, line.y2-line.y1)
        for point in ((line.x1, line.y1), (line.x2, line.y2)):
            candidates = [a for a in arcs if _near(point, _point(a, a.start_angle_deg)) or _near(point, _point(a, a.end_angle_deg))]
            if candidates:
                radial = (point[0]-candidates[0].x, point[1]-candidates[0].y)
                if abs(direction[0]*radial[0]+direction[1]*radial[1]) > TOLERANCE_MM:
                    failures.append("line/arc junction is not tangent")
                    break
    center_front = (sum(a.x for a in arcs)/2, sum(a.y for a in arcs)/2)
    overall = centre_distance + 2*radius
    width = 2*radius
    declared = (graph.feature_evidence or {}).get("straight_slot", {})
    expected = declared.get("expected", {})
    for key, actual in (("overall_length_mm", overall), ("width_mm", width)):
        if key in expected and abs(float(expected[key])-actual) > TOLERANCE_MM: failures.append(f"declared {key} conflicts with geometry")
    if "center_mm" in expected and math.dist(tuple(expected["center_mm"]), center_front) > TOLERANCE_MM:
        failures.append("declared slot center conflicts with geometry")
    if failures:
        return {"status": "FAIL", "error_code": "INPUT_INCONSISTENT", "contradictions": sorted(set(failures))}
    # Orthogonal evidence: separations express slot overall length and width; segments span the full depth.
    top_pairs, left_pairs = graph.top.hidden_line_pairs, graph.left.hidden_line_pairs
    if not top_pairs or not left_pairs:
        return {"status": "AMBIGUOUS", "reason": "insufficient orthogonal depth/through evidence", "candidates": ["STRAIGHT_SLOT", "UNKNOWN_SLOT_LIKE_CONTOUR"]}
    top_width = abs(top_pairs[0].offset_2-top_pairs[0].offset_1)
    left_width = abs(left_pairs[0].offset_2-left_pairs[0].offset_1)
    if abs(top_width-overall) > TOLERANCE_MM or abs(left_width-width) > TOLERANCE_MM:
        return {"status": "FAIL", "error_code": "INPUT_INCONSISTENT", "contradictions": ["cross-view slot width conflict"]}
    top_center_x = (top_pairs[0].offset_1+top_pairs[0].offset_2)/2
    side_center_y = (left_pairs[0].offset_1+left_pairs[0].offset_2)/2
    position_conflicts = []
    if abs(top_center_x-center_front[0]) > TOLERANCE_MM:
        position_conflicts.append("front/top slot X position conflict")
    if abs(side_center_y-center_front[1]) > TOLERANCE_MM:
        position_conflicts.append("front/side slot Y position conflict")
    if position_conflicts:
        return {"status": "FAIL", "error_code": "INPUT_INCONSISTENT", "contradictions": position_conflicts}
    if (center_front[0]-overall/2 < -TOLERANCE_MM or center_front[0]+overall/2 > w+TOLERANCE_MM
            or center_front[1]-width/2 < -TOLERANCE_MM or center_front[1]+width/2 > h+TOLERANCE_MM):
        return {"status": "FAIL", "error_code": "INPUT_INCONSISTENT", "contradictions": ["slot envelope crosses base boundary"]}
    spans_top = all(abs(abs(s.y2-s.y1)-graph.top.vertical_extent) <= TOLERANCE_MM for s in graph.top.hidden_segments)
    spans_left = all(abs(abs(s.x2-s.x1)-graph.left.horizontal_extent) <= TOLERANCE_MM for s in graph.left.hidden_segments)
    through_state = declared.get("through_state")
    if through_state != "THROUGH" or not spans_top or not spans_left:
        return {"status": "AMBIGUOUS", "reason": "blind vs through cannot be resolved", "candidates": ["STRAIGHT_SLOT", "UNKNOWN_SLOT_LIKE_CONTOUR"]}
    internal = front_to_internal(center_front[0], center_front[1], w, h)
    evidence = ["two_parallel_lines", "two_equal_radius_arcs", "endpoint_continuity", "closed_contour", "tangent_junctions", "width_consistent", "center_consistent", "cross_view_position_consistent", "orthogonal_depth_evidence", "through_state_evidence"]
    confidence = round(len(evidence) / 10.0, 3)
    return {"status": "PASS", "slot": StraightSlot(overall, width, radius, internal[0], internal[1], major_axis, True), "evidence": evidence, "confidence": confidence}


def infer_slots(graph):
    result = analyze_slot_contract(graph)
    if result["status"] == "NONE": return [], []
    if result["status"] == "PASS":
        return [result["slot"]], [FeatureHypothesis("STRAIGHT_SLOT", result["confidence"], result["evidence"])]
    return [], [FeatureHypothesis("UNKNOWN_SLOT_LIKE_CONTOUR", 0.0, [result.get("reason", "; ".join(result.get("contradictions", [])))], "AMBIGUOUS" if result["status"] == "AMBIGUOUS" else "FAIL")]
