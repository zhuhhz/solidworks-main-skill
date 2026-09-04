"""Tolerance-based primitive matching for Level-2 projected geometry."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

POSITION_TOLERANCE_MM = 0.10
RADIUS_TOLERANCE_MM = 0.05
SUPPORT_IOU_MIN = 0.98
MAX_GAP_MM = 0.10
MAX_OVERFLOW_RATIO = 0.02
ANGLE_TOLERANCE_DEG = 0.10
LINE_DISTANCE_TOLERANCE_MM = 0.10
_EPS = 1e-9


@dataclass
class _Support:
    direction: tuple[float, float]
    normal: tuple[float, float]
    offset: float
    expected: list[tuple[float, float]] = field(default_factory=list)
    actual: list[tuple[float, float]] = field(default_factory=list)
    expected_segment_count: int = 0
    actual_segment_count: int = 0


def _segment(line: dict):
    p1 = (float(line["x1"]), float(line["y1"]))
    p2 = (float(line["x2"]), float(line["y2"]))
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length <= _EPS:
        raise ValueError("zero-length projected line")
    direction = (dx / length, dy / length)
    if direction[0] < -_EPS or (abs(direction[0]) <= _EPS and direction[1] < 0):
        direction = (-direction[0], -direction[1])
    return p1, p2, direction


def _angle_difference_deg(a, b) -> float:
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    return math.degrees(math.acos(dot))


def _belongs(support: _Support, midpoint, direction) -> bool:
    distance = abs(support.normal[0] * midpoint[0] + support.normal[1] * midpoint[1] - support.offset)
    return _angle_difference_deg(support.direction, direction) <= ANGLE_TOLERANCE_DEG and distance <= LINE_DISTANCE_TOLERANCE_MM


def _add(supports: list[_Support], line: dict, side: str) -> None:
    p1, p2, direction = _segment(line)
    midpoint = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    support = next((item for item in supports if _belongs(item, midpoint, direction)), None)
    if support is None:
        normal = (-direction[1], direction[0])
        support = _Support(direction, normal, normal[0] * p1[0] + normal[1] * p1[1])
        supports.append(support)
    interval = sorted((
        support.direction[0] * p1[0] + support.direction[1] * p1[1],
        support.direction[0] * p2[0] + support.direction[1] * p2[1],
    ))
    getattr(support, side).append((interval[0], interval[1]))
    count_name = f"{side}_segment_count"
    setattr(support, count_name, getattr(support, count_name) + 1)


def _union(intervals):
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + _EPS:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _length(intervals) -> float:
    return sum(end - start for start, end in intervals)


def _intersection_length(left, right) -> float:
    i = j = 0
    total = 0.0
    while i < len(left) and j < len(right):
        total += max(0.0, min(left[i][1], right[j][1]) - max(left[i][0], right[j][0]))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return total


def _missing_intervals(expected, actual):
    missing = []
    for start, end in expected:
        cursor = start
        for other_start, other_end in actual:
            if other_end <= cursor or other_start >= end:
                continue
            if other_start > cursor:
                missing.append((cursor, min(other_start, end)))
            cursor = max(cursor, other_end)
            if cursor >= end:
                break
        if cursor < end:
            missing.append((cursor, end))
    return missing


def _interval_difference(source, subtract):
    """Return the parts of ``source`` not covered by ``subtract``."""
    return _missing_intervals(source, subtract)


def match_line_supports(expected: list[dict], actual: list[dict]) -> dict:
    supports: list[_Support] = []
    invalid = []
    for side, lines in (("expected", expected), ("actual", actual)):
        for index, line in enumerate(lines):
            try:
                _add(supports, line, side)
            except ValueError as exc:
                invalid.append({"side": side, "index": index, "error": str(exc)})

    expected_length = actual_length = intersection = 0.0
    max_gap = 0.0
    support_rows = []
    segmentation_different = False
    for support in supports:
        expected_union, actual_union = _union(support.expected), _union(support.actual)
        exp_len, act_len = _length(expected_union), _length(actual_union)
        common = _intersection_length(expected_union, actual_union)
        gaps = _missing_intervals(expected_union, actual_union)
        gap = max((_length([item]) for item in gaps), default=0.0)
        expected_length += exp_len
        actual_length += act_len
        intersection += common
        max_gap = max(max_gap, gap)
        same_support = abs(exp_len - act_len) <= POSITION_TOLERANCE_MM and abs(common - exp_len) <= POSITION_TOLERANCE_MM
        if same_support and support.expected_segment_count != support.actual_segment_count:
            segmentation_different = True
        support_rows.append({
            "direction": list(support.direction), "normal_offset_mm": support.offset,
            "expected_intervals": expected_union, "actual_intervals": actual_union,
            "expected_segment_count": support.expected_segment_count,
            "actual_segment_count": support.actual_segment_count,
            "intersection_length_mm": common, "max_gap_mm": gap,
        })

    union_length = expected_length + actual_length - intersection
    missing_length = max(0.0, expected_length - intersection)
    overflow_length = max(0.0, actual_length - intersection)
    support_iou = intersection / union_length if union_length > _EPS else 1.0
    missing_ratio = missing_length / expected_length if expected_length > _EPS else (0.0 if actual_length <= _EPS else 1.0)
    overflow_ratio = overflow_length / expected_length if expected_length > _EPS else (0.0 if actual_length <= _EPS else 1.0)
    passed = (
        not invalid and support_iou >= SUPPORT_IOU_MIN and max_gap <= MAX_GAP_MM
        and overflow_ratio <= MAX_OVERFLOW_RATIO and missing_ratio <= 1.0 - SUPPORT_IOU_MIN
    )
    return {
        "status": "PASS" if passed else "FAIL", "mode": "INFINITE_SUPPORT_LINE_INTERVAL_COVERAGE",
        "expected": len(expected), "actual": len(actual),
        "expected_support_length_mm": expected_length, "actual_support_length_mm": actual_length,
        "intersection_length_mm": intersection, "union_length_mm": union_length,
        "support_iou": support_iou, "missing_length_mm": missing_length,
        "overflow_length_mm": overflow_length, "missing_ratio": missing_ratio,
        "overflow_ratio": overflow_ratio, "max_gap_mm": max_gap,
        "segmentation": "SEGMENTATION_DIFFERENT" if segmentation_different else "EQUIVALENT_OR_UNASSESSED",
        "information": ["GEOMETRY_EQUIVALENT", "SEGMENTATION_DIFFERENT"] if passed and segmentation_different else (["GEOMETRY_EQUIVALENT"] if passed else []),
        "thresholds": {"support_iou_min": SUPPORT_IOU_MIN, "max_gap_mm": MAX_GAP_MM,
                       "max_overflow_ratio": MAX_OVERFLOW_RATIO, "angle_tolerance_deg": ANGLE_TOLERANCE_DEG,
                       "line_distance_tolerance_mm": LINE_DISTANCE_TOLERANCE_MM},
        "supports": support_rows, "invalid_segments": invalid,
        "precision": intersection / actual_length if actual_length > _EPS else (1.0 if expected_length <= _EPS else 0.0),
        "recall": intersection / expected_length if expected_length > _EPS else 1.0,
    }


def support_difference(base: list[dict], superset: list[dict]) -> dict:
    """Canonical support subtraction used by the HLV-minus-HLR experiment."""
    supports: list[_Support] = []
    for line in base:
        _add(supports, line, "expected")
    for line in superset:
        _add(supports, line, "actual")
    candidates = []
    for support in supports:
        base_union, superset_union = _union(support.expected), _union(support.actual)
        origin = (support.normal[0] * support.offset, support.normal[1] * support.offset)
        for start, end in _interval_difference(superset_union, base_union):
            if end - start <= POSITION_TOLERANCE_MM:
                continue
            candidates.append({
                "geometry_type": "LINE", "semantic": "HIDDEN",
                "source": "HLV_MINUS_HLR", "confidence": 1.0,
                "geometry": {
                    "x1": origin[0] + support.direction[0] * start,
                    "y1": origin[1] + support.direction[1] * start,
                    "x2": origin[0] + support.direction[0] * end,
                    "y2": origin[1] + support.direction[1] * end,
                },
                "support_length_mm": end - start,
            })
    coverage = match_line_supports(base, superset)
    visible_stable = coverage["missing_ratio"] <= 1.0 - SUPPORT_IOU_MIN and coverage["max_gap_mm"] <= MAX_GAP_MM
    return {"status": "PASS" if visible_stable else "FAIL", "visible_supports_stable": visible_stable,
            "candidates": candidates, "candidate_support_length_mm": sum(x["support_length_mm"] for x in candidates),
            "coverage": coverage}


def _circle_match(a: dict, b: dict) -> bool:
    return math.dist((a["x"], a["y"]), (b["x"], b["y"])) <= POSITION_TOLERANCE_MM and abs(a["diameter"] - b["diameter"]) / 2 <= RADIUS_TOLERANCE_MM


def match(expected: list[dict], actual: list[dict], kind: str) -> dict:
    if kind == "line":
        return match_line_supports(expected, actual)
    if kind != "circle":
        raise ValueError(f"unsupported primitive kind: {kind}")
    used, pairs = set(), []
    for i, source in enumerate(expected):
        found = next((j for j, target in enumerate(actual) if j not in used and _circle_match(source, target)), None)
        if found is not None:
            used.add(found)
            pairs.append((i, found))
    return {"status": "PASS" if len(pairs) == len(expected) == len(actual) else "FAIL", "expected": len(expected), "actual": len(actual), "matched": len(pairs), "missing": len(expected)-len(pairs), "extra": len(actual)-len(pairs), "precision": len(pairs)/len(actual) if actual else (1.0 if not expected else 0.0), "recall": len(pairs)/len(expected) if expected else 1.0, "pairs": pairs}
