from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from inference.evidence_binding import build_feature_graph_from_evidence
from inference.feature_hypothesis import infer_feature_graph
from parser.structured_input import load_structured_input
from schemas.view_geometry import HiddenLinePair
from validation.feature_graph_validator import validate_feature_graph
from validation.projection_consistency import validate as validate_projection


CASE = ROOT / "benchmarks" / "case_005_multi_feature.json"


def graph():
    return load_structured_input(CASE)


def test_hole_evidence_binding_passes_with_corresponding_views():
    features, attribution = build_feature_graph_from_evidence(graph())
    hole = features.holes[0]
    assert attribution["status"] == "PASS"
    assert attribution["features"]["hole_001"]["status"] == "ATTRIBUTED"
    assert (hole.diameter, hole.center_x, hole.center_y, hole.axis, hole.through) == (
        20, -25, -10, "Z", True,
    )
    assert set(hole.source_evidence_ids) == set(
        attribution["features"]["hole_001"]["evidence_ids"]
    )


def test_b005_structured_input_and_oracle_match_inferred_feature_graph():
    source = graph()
    features = infer_feature_graph(source)
    nodes = {node.feature_id: node for node in features.to_feature_nodes()}
    assert source.expected_features is not None
    assert validate_projection(source)["status"] == "PASS"
    assert set(nodes) == set(source.expected_features)
    for feature_id, expected in source.expected_features.items():
        assert nodes[feature_id].feature_type == expected["type"]
        assert nodes[feature_id].parameters == {key: value for key, value in expected.items() if key != "type"}


def test_slot_evidence_binding_passes_with_line_arc_and_depth_evidence():
    features, attribution = build_feature_graph_from_evidence(graph())
    slot = features.slots[0]
    assert attribution["features"]["slot_001"]["status"] == "ATTRIBUTED"
    assert (
        slot.overall_length_mm, slot.width_mm, slot.radius_mm,
        slot.center_x_mm, slot.center_y_mm, slot.major_axis, slot.through,
    ) == (40, 20, 10, 15, 8, "X", True)
    kinds = set(attribution["features"]["slot_001"]["geometry_types"])
    assert {"LINE", "ARC", "HIDDEN_LINE_PAIR", "HIDDEN_LINE"} <= kinds


def test_hole_and_slot_evidence_swapped_fails_without_owner_guessing():
    source = graph()
    records = list(source.feature_evidence_records)
    circle_index = next(i for i, row in enumerate(records) if row.geometry_reference == "front_hole_circle_001")
    arc_index = next(i for i, row in enumerate(records) if row.geometry_reference == "front_slot_arc_left_001")
    records[circle_index] = replace(records[circle_index], feature_id="slot_001")
    records[arc_index] = replace(records[arc_index], feature_id="hole_001")
    source.feature_evidence_records = records
    features, attribution = build_feature_graph_from_evidence(source)
    assert features.status == "FAIL"
    assert attribution["status"] == "FAIL"
    assert attribution["error_code"] == "EVIDENCE_ATTRIBUTION_INVALID"
    assert attribution["owner_guessing_used"] is False


def test_missing_required_feature_evidence_is_unattributed():
    source = graph()
    source.feature_evidence_records = [
        row for row in source.feature_evidence_records
        if row.geometry_reference != "top_hole_pair_001"
    ]
    features, attribution = build_feature_graph_from_evidence(source)
    assert features.status == "AMBIGUOUS"
    assert attribution["status"] == "UNATTRIBUTED"
    assert attribution["error_code"] == "UNATTRIBUTED"
    assert attribution["features"]["hole_001"]["status"] == "UNATTRIBUTED"
    assert "top_hole_pair_001" in attribution["unattributed_primitive_ids"]


def test_cross_view_hole_conflict_is_input_inconsistent():
    source = graph()
    index = next(
        i for i, pair in enumerate(source.top.hidden_line_pairs)
        if pair.primitive_id == "top_hole_pair_001"
    )
    source.top.hidden_line_pairs[index] = HiddenLinePair(
        axis="x", offset_1=10, offset_2=30, primitive_id="top_hole_pair_001"
    )
    features, attribution = build_feature_graph_from_evidence(source)
    assert features.status == "FAIL"
    assert attribution["status"] == "FAIL"
    assert attribution["error_code"] == "INPUT_INCONSISTENT"
    assert any("front/top hole X" in item for item in attribution["contradictions"])


def test_generated_feature_graph_has_independent_base_dependencies():
    features, attribution = build_feature_graph_from_evidence(graph())
    assert attribution["status"] == "PASS"
    assert validate_feature_graph(features)["status"] == "PASS"
    assert features.holes[0].dependencies == ["base_001"]
    assert features.slots[0].dependencies == ["base_001"]
    features.slots[0].dependencies = ["hole_001"]
    result = validate_feature_graph(features)
    assert result["status"] == "FAIL"
    assert result["error_code"] == "DEPENDENCY_VIOLATION"


def test_base_attribution_requires_actual_outer_contours():
    source = graph()
    records = list(source.feature_evidence_records)
    base_index = next(i for i, row in enumerate(records) if row.geometry_reference == "front_base_bottom_001")
    slot_index = next(i for i, row in enumerate(records) if row.geometry_reference == "front_slot_bottom_001")
    records[base_index] = replace(records[base_index], feature_id="slot_001")
    records[slot_index] = replace(records[slot_index], feature_id="base_001")
    source.feature_evidence_records = records
    features, attribution = build_feature_graph_from_evidence(source)
    assert features.status == "FAIL"
    assert attribution["status"] == "FAIL"
    assert attribution["owner_guessing_used"] is False


def test_operation_provenance_remains_traceable_from_generated_graph():
    from run_benchmark import build_plan
    from validation.feature_graph_validator import validate_modeling_plan

    features, _ = build_feature_graph_from_evidence(graph())
    plan = build_plan(features)
    assert validate_modeling_plan(features, plan)["status"] == "PASS"
    assert {
        operation.source_feature_id: operation.type for operation in plan.operations
    } == {
        "base_001": "base_extrude",
        "hole_001": "cut_extrude_through_circle",
        "slot_001": "cut_extrude_through_slot",
    }
