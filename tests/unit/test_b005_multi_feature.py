from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from schemas.feature_graph import BaseBlock, FeatureGraph, Hole, StraightSlot
from schemas.modeling_plan import ModelingOperation, ModelingPlan
from schemas.ownership_evidence import OwnershipEvidence
from validation.feature_attribution import validate_feature_attribution, validate_ownership_evidence
from validation.feature_graph_validator import validate_feature_graph, validate_modeling_plan
from validation.multi_feature_validator import validate_multi_feature_geometry


def feature_graph() -> FeatureGraph:
    return FeatureGraph(
        base_block=BaseBlock(
            100, 60, 20,
            feature_id="base_001",
            source_evidence_ids=["front_outer", "top_outer", "side_outer"],
            dependencies=[],
        ),
        holes=[Hole(
            20, -25, -10, "Z", True,
            feature_id="hole_001",
            source_evidence_ids=["front_hole_circle_001", "top_hole_hidden_pair_001", "side_hole_hidden_pair_001"],
            dependencies=["base_001"],
        )],
        slots=[StraightSlot(
            40, 20, 10, 15, 8, "X", True,
            feature_id="slot_001",
            source_evidence_ids=["front_slot_contour_001", "top_slot_hidden_set_001", "side_slot_hidden_pair_001"],
            dependencies=["base_001"],
        )],
    )


def modeling_plan(*, slot_first: bool = False) -> ModelingPlan:
    base = ModelingOperation(
        "base_extrude", "Front Plane",
        {"type": "rectangle", "width_mm": 100, "height_mm": 60}, 20,
        operation_id="op_base_001", source_feature_id="base_001",
        depends_on_operation_ids=[],
    )
    hole = ModelingOperation(
        "cut_extrude_through_circle", "Front Plane",
        {"type": "circle", "diameter_mm": 20, "center_x_mm": -25, "center_y_mm": -10},
        direction="through_all", operation_id="op_hole_001", source_feature_id="hole_001",
        depends_on_operation_ids=["op_base_001"],
    )
    slot = ModelingOperation(
        "cut_extrude_through_slot", "Front Plane",
        {"type": "straight_slot", "overall_length_mm": 40, "width_mm": 20,
         "radius_mm": 10, "center_x_mm": 15, "center_y_mm": 8, "major_axis": "X"},
        direction="through_all", operation_id="op_slot_001", source_feature_id="slot_001",
        depends_on_operation_ids=["op_base_001"],
    )
    return ModelingPlan([base, slot, hole] if slot_first else [base, hole, slot])


def measured_geometry() -> dict:
    return {
        "holes": [{"feature_id": "hole_001", "diameter_mm": 20, "center_mm": [-25, -10], "through": True}],
        "slots": [{"feature_id": "slot_001", "overall_length_mm": 40, "width_mm": 20,
                   "radius_mm": 10, "center_mm": [15, 8], "major_axis": "X", "through": True}],
    }


def test_feature_graph_exposes_required_multi_feature_node_contract():
    nodes = feature_graph().to_feature_nodes()
    assert [node.feature_id for node in nodes] == ["base_001", "hole_001", "slot_001"]
    assert {node.feature_type for node in nodes} == {"BASE_BLOCK", "THROUGH_HOLE", "STRAIGHT_SLOT"}
    for node in nodes:
        rendered = node.to_dict()
        assert set(("feature_id", "feature_type", "parameters", "source_evidence_ids", "dependencies")) <= rendered.keys()
        assert rendered["parameters"]


def test_dependency_graph_accepts_base_with_independent_hole_and_slot():
    result = validate_feature_graph(feature_graph())
    assert result["status"] == "PASS"
    assert result["topological_order"] == ["base_001", "hole_001", "slot_001"]


def test_floating_or_chained_cut_dependency_fails():
    floating = feature_graph(); floating.holes[0].dependencies = []
    assert validate_feature_graph(floating)["error_code"] == "DEPENDENCY_VIOLATION"
    chained = feature_graph(); chained.slots[0].dependencies = ["hole_001"]
    assert validate_feature_graph(chained)["error_code"] == "DEPENDENCY_VIOLATION"


def test_operation_provenance_maps_each_feature_to_expected_operation():
    result = validate_modeling_plan(feature_graph(), modeling_plan())
    assert result["status"] == "PASS"
    assert result["classification"] == "CANONICAL_ORDER"
    assert result["feature_operations"] == {
        "base_001": "base_extrude",
        "hole_001": "cut_extrude_through_circle",
        "slot_001": "cut_extrude_through_slot",
    }


def test_valid_independent_feature_order_is_equivalent_not_failure():
    result = validate_modeling_plan(feature_graph(), modeling_plan(slot_first=True))
    assert result["status"] == "PASS"
    assert result["classification"] == "ORDER_VARIANT_EQUIVALENT"


def test_invalid_operation_dependency_order_fails():
    plan = modeling_plan()
    plan.operations[0].depends_on_operation_ids = ["op_hole_001"]
    assert validate_modeling_plan(feature_graph(), plan)["error_code"] == "DEPENDENCY_VIOLATION"


def test_hole_diameter_wrong_fails_multi_feature_geometry():
    actual = measured_geometry(); actual["holes"][0]["diameter_mm"] = 18
    assert validate_multi_feature_geometry(feature_graph(), actual)["status"] == "FAIL"


def test_slot_position_wrong_fails_multi_feature_geometry():
    actual = measured_geometry(); actual["slots"][0]["center_mm"] = [10, 8]
    assert validate_multi_feature_geometry(feature_graph(), actual)["status"] == "FAIL"


def test_missing_hole_fails_multi_feature_geometry():
    actual = measured_geometry(); actual["holes"] = []
    result = validate_multi_feature_geometry(feature_graph(), actual)
    assert result["status"] == "FAIL"
    assert result["missing_feature_ids"] == ["hole_001"]


def ownership_rows() -> list[OwnershipEvidence]:
    return [
        OwnershipEvidence("face_base_outer", "FACE", "base_001", "IFace2.GetFeature", "API_EXACT"),
        OwnershipEvidence("face_hole_wall", "FACE", "hole_001", "IFace2.GetFeature", "API_EXACT"),
        OwnershipEvidence("face_slot_end_1", "FACE", "slot_001", "IFace2.GetFeature", "API_EXACT"),
        OwnershipEvidence("face_slot_end_2", "FACE", "slot_001", "IFace2.GetFeature", "API_EXACT"),
    ]


def test_exact_ownership_evidence_passes_without_using_feature_names():
    expected = {"face_base_outer": "base_001", "face_hole_wall": "hole_001",
                "face_slot_end_1": "slot_001", "face_slot_end_2": "slot_001"}
    result = validate_ownership_evidence(expected, ownership_rows())
    assert result["status"] == "PASS"
    assert result["unresolved_count"] == 0


def test_swapped_feature_ownership_fails():
    rows = ownership_rows()
    rows[1] = OwnershipEvidence("face_hole_wall", "FACE", "slot_001", "IFace2.GetFeature", "API_EXACT")
    rows[2] = OwnershipEvidence("face_slot_end_1", "FACE", "hole_001", "IFace2.GetFeature", "API_EXACT")
    expected = {"face_base_outer": "base_001", "face_hole_wall": "hole_001",
                "face_slot_end_1": "slot_001", "face_slot_end_2": "slot_001"}
    assert validate_ownership_evidence(expected, rows)["status"] == "FAIL"


def test_unresolved_ownership_is_not_guessed():
    rows = [OwnershipEvidence("face_hole_wall", "FACE", None, "IFace2.GetFeature", "OWNERSHIP_UNRESOLVED")]
    result = validate_ownership_evidence({"face_hole_wall": "hole_001"}, rows)
    assert result["status"] == "FAIL"
    assert result["unresolved_count"] == 1


def test_level2_outer_attribution_rejects_swapped_owner_even_when_geometry_matches():
    matches = [
        {"primitive_id": "top_hole_hidden_1", "expected_feature_id": "hole_001",
         "actual_feature_id": "slot_001", "geometry_status": "PASS", "semantic": "HIDDEN"},
        {"primitive_id": "top_slot_hidden_1", "expected_feature_id": "slot_001",
         "actual_feature_id": "hole_001", "geometry_status": "PASS", "semantic": "HIDDEN"},
    ]
    result = validate_feature_attribution(matches, unknown_count=0)
    assert result["status"] == "FAIL"
    assert result["unattributed_count"] == 0
    assert result["misattributed_count"] == 2


def test_level2_requires_unknown_and_unattributed_zero():
    attributed = [{"primitive_id": "front_hole", "expected_feature_id": "hole_001",
                   "actual_feature_id": "hole_001", "geometry_status": "PASS", "semantic": "VISIBLE"}]
    assert validate_feature_attribution(attributed, unknown_count=0)["status"] == "PASS"
    missing = [{**attributed[0], "actual_feature_id": None}]
    assert validate_feature_attribution(missing, unknown_count=0)["status"] == "FAIL"
    assert validate_feature_attribution(attributed, unknown_count=1)["status"] == "FAIL"
