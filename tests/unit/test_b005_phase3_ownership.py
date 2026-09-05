from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from backend.ownership_probe import build_owned_geometry_summary, classify_face_role, validate_face_ownership_rows
from drawing.drawing_feature_attribution import _expected_rows, select_topological_owner, validate_attributed_roundtrip
from parser.structured_input import load_structured_input


def row(entity_id, role, expected, actual, *, ownership="API_EXACT", geometry=None):
    return {
        "entity_id": entity_id,
        "logical_role": role,
        "expected_feature_id": expected,
        "feature_id": actual,
        "ownership": ownership,
        "source": "IFace2.GetFeature+IModelDocExtension.GetPersistReference3",
        "owner_type": "ICE",
        "geometry": geometry or {},
    }


def valid_rows():
    base = [row(f"base_{index}", "BASE_SURFACE", "base_001", "base_001") for index in range(6)]
    hole = [row("hole_wall", "HOLE_WALL", "hole_001", "hole_001", geometry={
        "diameter_mm": 20, "origin_mm": [-25, -10, -20], "axis": [0, 0, 1],
        "bounding_box_mm": [-35, -20, -20, -15, 0, 0],
    })]
    ends = [
        row("slot_end_1", "SLOT_END_WALL", "slot_001", "slot_001", geometry={
            "radius_mm": 10, "origin_mm": [5, 8, -20], "bounding_box_mm": [-5, -2, -20, 15, 18, 0]}),
        row("slot_end_2", "SLOT_END_WALL", "slot_001", "slot_001", geometry={
            "radius_mm": 10, "origin_mm": [25, 8, -20], "bounding_box_mm": [15, -2, -20, 35, 18, 0]}),
    ]
    sides = [
        row("slot_side_1", "SLOT_SIDE_WALL", "slot_001", "slot_001", geometry={"origin_mm": [5, -2, -20]}),
        row("slot_side_2", "SLOT_SIDE_WALL", "slot_001", "slot_001", geometry={"origin_mm": [5, 18, -20]}),
    ]
    return base + hole + ends + sides


def test_face_role_classification_separates_base_hole_and_slot_without_names():
    assert classify_face_role({"surface_type":"PLANE", "internal":False, "edge_count":4, "normal":[1, 0, 0]}) == ("BASE_SURFACE", "base_001")
    assert classify_face_role({"surface_type":"PLANE", "internal":True, "edge_count":9, "normal":[0, 0, -1]}) == ("BASE_SURFACE", "base_001")
    assert classify_face_role({"surface_type":"CYLINDER", "internal":True, "edge_count":2}) == ("HOLE_WALL", "hole_001")
    assert classify_face_role({"surface_type":"CYLINDER", "internal":True, "edge_count":4}) == ("SLOT_END_WALL", "slot_001")
    assert classify_face_role({"surface_type":"PLANE", "internal":True, "edge_count":4, "normal":[0, 1, 0]}) == ("SLOT_SIDE_WALL", "slot_001")


def test_exact_multi_feature_face_ownership_passes():
    result = validate_face_ownership_rows(valid_rows())
    assert result["status"] == "PASS"
    assert result["gate"]["unresolved_count"] == 0


def test_hole_ownership_swap_fails():
    rows = valid_rows(); rows[6]["feature_id"] = "slot_001"
    result = validate_face_ownership_rows(rows)
    assert result["status"] == "FAIL"
    assert result["gate"]["misattributed_count"] == 1


def test_slot_ownership_swap_fails():
    rows = valid_rows(); rows[7]["feature_id"] = "hole_001"
    result = validate_face_ownership_rows(rows)
    assert result["status"] == "FAIL"
    assert result["gate"]["misattributed_count"] == 1


def test_missing_hole_or_slot_api_evidence_is_unresolved():
    rows = valid_rows(); rows[6].update(feature_id=None, ownership="OWNERSHIP_UNRESOLVED")
    assert validate_face_ownership_rows(rows)["gate"]["unresolved_count"] == 1
    rows = valid_rows(); rows[7].update(feature_id=None, ownership="OWNERSHIP_UNRESOLVED")
    assert validate_face_ownership_rows(rows)["gate"]["unresolved_count"] == 1


def test_geometry_correct_but_owner_wrong_does_not_build_owned_geometry():
    rows = valid_rows(); rows[6]["feature_id"] = "slot_001"
    ownership = validate_face_ownership_rows(rows)
    operations = [
        {"source_feature_id":"hole_001", "evidence":{"through":True}},
        {"source_feature_id":"slot_001", "evidence":{"through":True}},
    ]
    measured = build_owned_geometry_summary(ownership, operations, 20)
    assert ownership["status"] == "FAIL"
    assert measured["holes"] == []


def test_owned_geometry_preserves_hole_and_slot_parameters():
    ownership = validate_face_ownership_rows(valid_rows())
    operations = [
        {"source_feature_id":"hole_001", "evidence":{"through":True}},
        {"source_feature_id":"slot_001", "evidence":{"through":True}},
    ]
    measured = build_owned_geometry_summary(ownership, operations, 20)
    assert measured["holes"][0] | {"entity_ids": []} == {
        "feature_id":"hole_001", "diameter_mm":20, "center_mm":[-25, -10],
        "axis":[0, 0, 1], "through":True, "axial_extent_mm":20, "entity_ids":[],
    }
    slot = measured["slots"][0]
    assert (slot["overall_length_mm"], slot["width_mm"], slot["radius_mm"], slot["center_mm"], slot["major_axis"], slot["through"]) == (
        40, 20, 10, [15, 8], "X", True,
    )


def test_projected_edge_owner_uses_exact_topology_not_distance_or_name():
    assert select_topological_owner(["base_001", "hole_001"]) == "hole_001"
    assert select_topological_owner(["slot_001", "base_001"]) == "slot_001"
    assert select_topological_owner(["base_001", "base_001"]) == "base_001"
    assert select_topological_owner(["hole_001", "slot_001"]) is None
    assert select_topological_owner([]) is None


def attributed_semantic_graph():
    graph = load_structured_input(ROOT / "benchmarks" / "case_005_multi_feature.json")
    expected = _expected_rows(graph)
    views = []
    for view_name in ("front", "top", "left"):
        rows = [dict(row, actual_feature_id=row["expected_feature_id"], ownership="API_EXACT")
                for row in expected if row["semantic_view"] == view_name]
        views.append({"semantic_view": view_name, "rows": rows})
    return graph, {"status": "PASS", "views": views, "unknown_count": 0, "unattributed_count": 0}


def test_feature_attributed_level2_accepts_exact_partitions():
    graph, semantic = attributed_semantic_graph()
    assert validate_attributed_roundtrip(graph, semantic)["status"] == "PASS"


def test_feature_attributed_level2_rejects_swap_missing_and_unknown():
    graph, semantic = attributed_semantic_graph()
    hole = next(row for view in semantic["views"] for row in view["rows"]
                if row["expected_feature_id"] == "hole_001")
    hole["actual_feature_id"] = "slot_001"
    assert validate_attributed_roundtrip(graph, semantic)["status"] == "FAIL"
    graph, semantic = attributed_semantic_graph()
    semantic["unattributed_count"] = 1
    assert validate_attributed_roundtrip(graph, semantic)["status"] == "FAIL"
    graph, semantic = attributed_semantic_graph()
    semantic["unknown_count"] = 1
    assert validate_attributed_roundtrip(graph, semantic)["status"] == "FAIL"
