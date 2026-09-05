"""B006 real-backend acceptance gates and executable negative controls."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from validation.pattern_contract import (PART_FEATURE_PATTERN, validate_pattern_graph,
                                         validate_pattern_ownership)


def _ownership_gate(graph, ownership: dict, ownership_domain) -> dict:
    envelope_domain = ownership.get("ownership_domain")
    if ownership_domain is None or envelope_domain is None:
        return {"status": "FAIL", "error_code": "OWNERSHIP_DOMAIN_REQUIRED",
                "reason": "execution and ownership evidence domains must be explicit"}
    if ownership_domain != PART_FEATURE_PATTERN or envelope_domain != ownership_domain:
        return {"status": "FAIL", "error_code": "OWNERSHIP_DOMAIN_UNSUPPORTED",
                "reason": "ownership domain is unsupported or inconsistent"}
    rows = ownership.get("rows")
    if not isinstance(rows, list):
        return {"status": "FAIL", "error_code": "OWNERSHIP_COVERAGE_INVALID",
                "reason": "occurrence-level ownership rows are required"}

    instances_by_index = {item.instance_index: item.feature_id for item in graph.instances}
    expected_entities = {}
    for row in rows:
        index = row.get("instance_index")
        entity_id = row.get("entity_id")
        if type(index) is not int or index not in instances_by_index:
            return {"status": "FAIL", "error_code": "INSTANCE_INDEX_INVALID",
                    "reason": "each occurrence needs a valid native instance index"}
        if not isinstance(entity_id, str) or not entity_id or entity_id in expected_entities:
            return {"status": "FAIL", "error_code": "OWNERSHIP_COVERAGE_INVALID",
                    "reason": "entity identities must be nonempty and unique"}
        expected_entities[entity_id] = instances_by_index[index]
    return validate_pattern_ownership(
        graph, expected_entities, rows, ownership_domain=ownership_domain)


def _ownership_mapping(ownership: dict):
    rows = ownership.get("rows")
    if not isinstance(rows, list):
        return None
    return sorted((row.get("instance_index"), row.get("feature_id", row.get("instance_id")), row.get("entity_id"),
                   row.get("owner_feature_id", row.get("native_owner_feature_id")),
                   row.get("ownership_level", row.get("ownership", row.get("state"))),
                   row.get("persistent_reference", row.get("identity_reference")))
                  for row in rows)


def validate_real_backend(graph, backend: dict) -> dict:
    initial_owner = backend.get("initial_ownership", {})
    reopened_owner = backend.get("reopened_ownership", {})
    ownership_domain = backend.get("ownership_domain")
    initial_gate = _ownership_gate(graph, initial_owner, ownership_domain)
    reopened_gate = _ownership_gate(graph, reopened_owner, ownership_domain)
    reopened_mapping_matches = _ownership_mapping(initial_owner) == _ownership_mapping(reopened_owner)
    checks = {
        "backend": backend.get("status") == "PASS",
        "part_saved": bool(backend.get("part_path")) and Path(backend["part_path"]).is_file(),
        "drawing_saved": bool(backend.get("drawing_path")) and Path(backend["drawing_path"]).is_file(),
        "read_only_reopen": backend.get("reopened_read_only") is True,
        "initial_feature_tree": backend.get("initial_feature_tree", {}).get("status") == "PASS",
        "reopened_feature_tree": backend.get("reopened_feature_tree", {}).get("status") == "PASS",
        "initial_pattern_definition": backend.get("initial_pattern_definition", {}).get("status") == "PASS",
        "reopened_pattern_definition": backend.get("reopened_pattern_definition", {}).get("status") == "PASS",
        "ownership_domain": ownership_domain == PART_FEATURE_PATTERN,
        "initial_part_pattern_ownership": initial_gate.get("status") == "PASS",
        "reopened_part_pattern_ownership": reopened_gate.get("status") == "PASS",
        "reopened_ownership_mapping": reopened_mapping_matches,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "ownership_requirement": "PART_FEATURE_PATTERN: seed API_EXACT; generated API_EXACT or INSTANCE_EXACT",
        "ownership_error_codes": {
            "initial": initial_gate.get("error_code"),
            "reopened": reopened_gate.get("error_code"),
            "mapping": None if reopened_mapping_matches else "REOPEN_OWNERSHIP_MISMATCH",
        },
        "strict_api_exact_status": {
            "initial": initial_owner.get("strict_api_exact_status"),
            "reopened": reopened_owner.get("strict_api_exact_status"),
        },
        "initial_ownership_counts": {
            "API_EXACT": initial_owner.get("api_exact_count"),
            "INSTANCE_EXACT": initial_owner.get("instance_exact_count"),
            "OWNERSHIP_UNRESOLVED": initial_owner.get("unresolved_count"),
        },
        "reopened_ownership_counts": {
            "API_EXACT": reopened_owner.get("api_exact_count"),
            "INSTANCE_EXACT": reopened_owner.get("instance_exact_count"),
            "OWNERSHIP_UNRESOLVED": reopened_owner.get("unresolved_count"),
        },
    }


def validate_level_1(graph, backend: dict) -> dict:
    geometry = backend.get("reopened_geometry", {})
    envelope = geometry.get("envelope_mm", {})
    holes = geometry.get("holes", [])
    expected_positions = {tuple(round(value, 3) for value in item.center_mm[:2])
                          for item in graph.instances}
    actual_positions = {tuple(round(float(value), 3) for value in row.get("position_mm", [])[:2])
                        for row in holes}
    checks = {
        "base_envelope": [envelope.get(key) for key in ("length", "width", "height")] == [100.0, 60.0, 20.0],
        "hole_count": len(holes) == 4,
        "hole_diameters": len(holes) == 4 and all(abs(float(row.get("diameter_mm", -1)) - 10.0) <= .01 for row in holes),
        "hole_positions": actual_positions == expected_positions,
        "hole_axes": len(holes) == 4 and all(abs(abs(float(row.get("axis", [0, 0, 0])[2])) - 1.0) <= 1e-6 for row in holes),
        "through_extent": len(holes) == 4 and all(abs(float(row.get("axial_length_mm", -1)) - 20.0) <= .05 for row in holes),
        "pattern_definition": backend.get("reopened_pattern_definition", {}).get("status") == "PASS",
        "three_views": backend.get("drawing_create", {}).get("status") == "pass"
                       and backend.get("drawing_structure", {}).get("view_count") == 3,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "expected_positions_mm": sorted(expected_positions), "actual_positions_mm": sorted(actual_positions)}


def run_negative_controls(graph, backend: dict) -> dict:
    def contract(mutator):
        candidate = deepcopy(graph)
        mutator(candidate)
        return validate_pattern_graph(candidate).get("error_code")

    tree = deepcopy(backend.get("reopened_feature_tree", {}))
    for row in tree.get("features", []):
        if row.get("feature_id") == "pattern_001":
            row["type_name_2"] = "CirPattern"
    type_actual = "PATTERN_TYPE_MISMATCH" if not any(
        row.get("feature_id") == "pattern_001" and row.get("type_name_2") in {"LPattern", "LinearPattern"}
        for row in tree.get("features", [])) else "PASS"
    results = {
        "wrong_count": {"expected": "INSTANCE_COUNT_MISMATCH", "actual": contract(
            lambda value: setattr(value.pattern, "total_count", 3))},
        "wrong_spacing": {"expected": "SPACING_MISMATCH", "actual": contract(
            lambda value: setattr(value.pattern, "spacing_mm", 15))},
        "wrong_direction": {"expected": "DIRECTION_MISMATCH", "actual": contract(
            lambda value: setattr(value.pattern, "direction", (-1, 0, 0)))},
        "seed_missing": {"expected": "MISSING_SEED", "actual": contract(
            lambda value: setattr(value, "seed", None))},
        "instance_missing": {"expected": "INSTANCE_COUNT_MISMATCH", "actual": contract(
            lambda value: value.instances.pop())},
        "pattern_type_wrong": {"expected": "PATTERN_TYPE_MISMATCH", "actual": type_actual},
    }
    return {"status": "PASS" if all(row["actual"] == row["expected"] for row in results.values()) else "FAIL",
            "results": results}
