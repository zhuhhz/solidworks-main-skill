"""ID-based Level-1 geometry contract; no CAD or name-based ownership logic."""
from __future__ import annotations

import math

from schemas.feature_graph import FeatureGraph


def _near(left, right, tolerance_mm: float) -> bool:
    return abs(float(left) - float(right)) <= tolerance_mm


def _center_near(actual, expected, tolerance_mm: float) -> bool:
    return isinstance(actual, (list, tuple)) and len(actual) >= 2 and math.dist(
        [float(actual[0]), float(actual[1])], [float(expected[0]), float(expected[1])]
    ) <= tolerance_mm


def validate_multi_feature_geometry(graph: FeatureGraph, measured: dict,
                                    tolerance_mm: float = 0.05) -> dict:
    expected_nodes = [node for node in graph.to_feature_nodes()
                      if node.feature_type in {"THROUGH_HOLE", "STRAIGHT_SLOT"}]
    actual_rows = [*measured.get("holes", []), *measured.get("slots", [])]
    counts: dict[str, int] = {}
    for row in actual_rows:
        feature_id = row.get("feature_id")
        counts[feature_id] = counts.get(feature_id, 0) + 1
    actual_by_id = {row.get("feature_id"): row for row in actual_rows if row.get("feature_id")}
    expected_ids = [node.feature_id for node in expected_nodes]
    missing = sorted(set(expected_ids) - set(actual_by_id))
    extra = sorted(set(actual_by_id) - set(expected_ids))
    duplicates = sorted(feature_id for feature_id, count in counts.items() if feature_id and count > 1)
    checks = []
    for node in expected_nodes:
        actual = actual_by_id.get(node.feature_id)
        if actual is None:
            continue
        expected = node.parameters
        if node.feature_type == "THROUGH_HOLE":
            passed = (
                _near(actual.get("diameter_mm", -999), expected["diameter_mm"], tolerance_mm)
                and _center_near(actual.get("center_mm"),
                                 [expected["center_x_mm"], expected["center_y_mm"]], tolerance_mm)
                and actual.get("through") is expected["through"]
            )
        else:
            passed = (
                all(_near(actual.get(key, -999), expected[key], tolerance_mm)
                    for key in ("overall_length_mm", "width_mm", "radius_mm"))
                and _center_near(actual.get("center_mm"),
                                 [expected["center_x_mm"], expected["center_y_mm"]], tolerance_mm)
                and actual.get("major_axis") == expected["major_axis"]
                and actual.get("through") is expected["through"]
            )
        checks.append({"feature_id": node.feature_id, "feature_type": node.feature_type,
                       "passed": passed, "expected": expected, "actual": actual})

    passed = not missing and not extra and not duplicates and all(check["passed"] for check in checks)
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "missing_feature_ids": missing,
        "extra_feature_ids": extra,
        "duplicate_feature_ids": duplicates,
    }
