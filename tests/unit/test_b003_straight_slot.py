from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from inference.feature_hypothesis import infer_feature_graph
from inference.slot_inference import analyze_slot_contract
from parser.structured_input import load_structured_input
from schemas.view_geometry import Arc
from validation.primitive_matcher import match_arc_supports
from validation.projection_consistency import validate
from drawing.drawing_geometry_extractor import _line_or_circle

CASE = ROOT / "benchmarks" / "case_003_straight_slot.json"


def graph():
    return load_structured_input(CASE)


def arc(start, end, direction="CCW"):
    return {"x": 0, "y": 0, "radius": 10, "start_angle_deg": start,
            "end_angle_deg": end, "sweep_direction": direction}


def test_arc_schema_normalizes_degrees_and_preserves_explicit_sweep():
    value = Arc(0, 0, 10, -90, 90, "cw")
    assert (value.start_angle_deg, value.end_angle_deg, value.sweep_direction, value.sweep_deg) == (270, 90, "CW", 180)


@pytest.mark.parametrize("kwargs", [
    {"radius": 0, "start_angle_deg": 0, "end_angle_deg": 90},
    {"radius": 10, "start_angle_deg": 0, "end_angle_deg": 90, "sweep_direction": "AUTO"},
    {"radius": 10, "start_angle_deg": 0, "end_angle_deg": 360},
])
def test_arc_schema_rejects_invalid_or_full_circle(kwargs):
    with pytest.raises(ValueError): Arc(0, 0, **kwargs)


def test_b003_contract_infers_engineering_slot_and_length_semantics():
    value = graph(); result = infer_feature_graph(value)
    assert validate(value)["status"] == "PASS"
    assert result.status == "PASS"
    assert result.slots[0].type == "STRAIGHT_SLOT"
    assert (result.slots[0].overall_length_mm, result.slots[0].width_mm, result.slots[0].radius_mm) == (40, 20, 10)
    assert result.slots[0].center_x_mm == result.slots[0].center_y_mm == 0
    assert result.hypotheses[-1].confidence == 1.0
    assert len(value.top.hidden_segments) == 4
    assert value.reference_integrity["history_status"] == "REFERENCE_INVALID"


def test_only_face_view_is_ambiguous():
    value = graph(); value.top.hidden_line_pairs=[]; value.left.hidden_line_pairs=[]
    assert analyze_slot_contract(value)["status"] == "AMBIGUOUS"
    assert infer_feature_graph(value).status == "AMBIGUOUS"


def test_cross_view_width_conflict_is_input_inconsistent():
    value = graph(); value.left.hidden_line_pairs[0] = type(value.left.hidden_line_pairs[0])("y", 21, 39)
    assert validate(value)["error_code"] == "INPUT_INCONSISTENT"


def test_end_arc_radius_mismatch_is_input_inconsistent():
    value = graph(); value.front.arcs[1] = Arc(60, 30, 9, 270, 90, "CCW")
    assert validate(value)["error_code"] == "INPUT_INCONSISTENT"


def test_line_arc_not_tangent_is_input_inconsistent():
    value = graph(); line=value.front.visible_segments[-2]
    value.front.visible_segments[-2] = type(line)(line.x1, line.y1, line.x2, line.y2+1)
    assert validate(value)["error_code"] == "INPUT_INCONSISTENT"


def test_open_contour_is_input_inconsistent():
    value = graph(); value.front.visible_segments.pop()
    assert validate(value)["error_code"] == "INPUT_INCONSISTENT"


def test_blind_vs_through_missing_evidence_is_ambiguous():
    value = graph(); value.feature_evidence["straight_slot"].pop("through_state")
    assert analyze_slot_contract(value)["status"] == "AMBIGUOUS"


def test_same_arc_support_with_split_segmentation_passes():
    result = match_arc_supports([arc(0,180)], [arc(0,90), arc(90,180)])
    assert result["status"] == "PASS"
    assert result["information"] == ["GEOMETRY_EQUIVALENT", "SEGMENTATION_DIFFERENT"]


def test_real_angular_gap_fails():
    assert match_arc_supports([arc(0,180)], [arc(0,89), arc(90,180)])["status"] == "FAIL"


def test_real_arc_overflow_fails():
    assert match_arc_supports([arc(0,180)], [arc(355,185)])["status"] == "FAIL"


def test_wrong_declared_slot_center_is_input_inconsistent():
    value = graph(); value.feature_evidence["straight_slot"]["expected"]["center_mm"] = [49,30]
    assert validate(value)["error_code"] == "INPUT_INCONSISTENT"


def test_arc_tolerance_configuration_is_reported_without_changing_line_thresholds():
    result = match_arc_supports([arc(0,180)], [arc(0,180)])
    assert result["thresholds"]["arc_max_gap_deg"] == .25
    from validation import primitive_matcher
    assert primitive_matcher.MAX_GAP_MM == .10


def test_solidworks_curve_record_is_extracted_as_arc_not_polyline_or_circle():
    angles = [90, 120, 150, 180, 210, 240, 260, 270]
    points = []
    for angle in angles:
        points += [.01*math.cos(math.radians(angle)), .01*math.sin(math.radians(angle)), 0]
    kind, value = _line_or_circle(1, points, 1.0, [0,0,0, 0,.01,0, 0,-.01,0, 0,0,1])
    assert kind == "arc"
    assert value["radius"] == pytest.approx(10)
    assert value["sweep_direction"] == "CCW"
