"""B005 real-backend gates and executable negative controls."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from backend.ownership_probe import build_owned_geometry_summary, validate_face_ownership_rows
from schemas.modeling_plan import ModelingPlan
from validation.feature_graph_validator import validate_modeling_plan
from validation.multi_feature_validator import validate_multi_feature_geometry


def validate_real_backend(features, plan, backend: dict) -> dict:
    initial_geometry = validate_multi_feature_geometry(features, backend.get("owned_geometry", {}))
    reopened_geometry = validate_multi_feature_geometry(features, backend.get("reopened_owned_geometry", {}))
    checks = {
        "backend": backend.get("status") == "PASS",
        "part_saved": bool(backend.get("part_path")) and Path(backend["part_path"]).is_file(),
        "drawing_saved": bool(backend.get("drawing_path")) and Path(backend["drawing_path"]).is_file(),
        "initial_feature_tree": backend.get("initial_feature_tree", {}).get("status") == "PASS",
        "reopened_feature_tree": backend.get("reopened_feature_tree", {}).get("status") == "PASS",
        "initial_ownership": backend.get("initial_ownership", {}).get("status") == "PASS",
        "reopened_ownership": backend.get("reopened_ownership", {}).get("status") == "PASS",
        "initial_multi_feature_geometry": initial_geometry.get("status") == "PASS",
        "reopened_multi_feature_geometry": reopened_geometry.get("status") == "PASS",
        "modeling_plan_provenance": validate_modeling_plan(features, plan).get("status") == "PASS",
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "initial_geometry": initial_geometry, "reopened_geometry": reopened_geometry}


def run_negative_controls(features, plan, backend: dict) -> dict:
    source_rows = backend.get("reopened_ownership", {}).get("rows", [])

    def changed(role, feature_id=None, ownership=None):
        rows = deepcopy(source_rows)
        row = next(item for item in rows if item.get("logical_role") == role)
        row["feature_id"] = feature_id
        if ownership is not None:
            row["ownership"] = ownership
        return rows

    hole_swap = validate_face_ownership_rows(changed("HOLE_WALL", "slot_001"))
    slot_swap = validate_face_ownership_rows(changed("SLOT_END_WALL", "hole_001"))
    missing_hole = validate_face_ownership_rows(changed("HOLE_WALL", None, "OWNERSHIP_UNRESOLVED"))
    missing_slot = validate_face_ownership_rows(changed("SLOT_END_WALL", None, "OWNERSHIP_UNRESOLVED"))
    wrong_owner_summary = build_owned_geometry_summary(hole_swap, backend.get("operations", []),
                                                        features.base_block.depth)
    wrong_owner_geometry = validate_multi_feature_geometry(features, wrong_owner_summary)
    variant = ModelingPlan([plan.operations[0], plan.operations[2], plan.operations[1]])
    invalid = deepcopy(plan)
    invalid.operations[1] = replace(invalid.operations[1], depends_on_operation_ids=["op_slot_001"])
    results = {
        "hole_ownership_swap": {"expected": "FAIL", "actual": hole_swap["status"]},
        "slot_ownership_swap": {"expected": "FAIL", "actual": slot_swap["status"]},
        "missing_hole_evidence": {"expected": "UNATTRIBUTED", "actual": "UNATTRIBUTED" if missing_hole["gate"]["unresolved_count"] else "FAIL"},
        "missing_slot_evidence": {"expected": "UNATTRIBUTED", "actual": "UNATTRIBUTED" if missing_slot["gate"]["unresolved_count"] else "FAIL"},
        "geometry_correct_owner_wrong": {"expected": "FAIL", "actual": wrong_owner_geometry["status"]},
        "feature_order_valid_but_different": {"expected": "ORDER_VARIANT_EQUIVALENT", "actual": validate_modeling_plan(features, variant).get("classification")},
        "invalid_dependency": {"expected": "DEPENDENCY_VIOLATION", "actual": validate_modeling_plan(features, invalid).get("error_code")},
    }
    return {"status": "PASS" if all(row["actual"] == row["expected"] for row in results.values()) else "FAIL",
            "results": results}
