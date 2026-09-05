from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from drawing.view_coordinate_transform import normalize_geometry, to_view_local_mm
from inference.feature_hypothesis import infer_feature_graph
from parser.structured_input import load_structured_input
from run_benchmark import build_plan
from schemas.view_geometry import HiddenLinePair
from validation.primitive_matcher import match_arc_supports, match_line_supports
from validation.projection_consistency import validate as validate_projection
from validation.reconstruction_validator import validate as validate_reconstruction
from validation.roundtrip_validator import validate as validate_level1
from validation.negative_tests import run as run_negative_tests

CASE = ROOT / "benchmarks" / "case_004_offset_slot.json"


def graph(): return load_structured_input(CASE)


def backend_at(cx=15, cy=8):
    return {"status":"PASS", "drawing_create":{"status":"pass"}, "drawing_structure":{"view_count":3},
            "model_summary":{"features":[{"name":"BaseBlock","type":"Extrusion"},{"name":"ThroughSlot_L40_W20","type":"ICE"}]},
            "operations":[{"operation":"cut_extrude_through_slot","evidence":{"through":True}}],
            "geometry":{"envelope_mm":{"length":100,"width":60,"height":20}, "holes":[],
                "slot_arc_candidates":[
                    {"diameter_mm":20,"position_mm":[cx-10,cy,-20],"axis":[0,0,1],"axial_length_mm":10,"measurement_source":"B-Rep internal cylindrical face"},
                    {"diameter_mm":20,"position_mm":[cx+10,cy,-20],"axis":[0,0,1],"axial_length_mm":10,"measurement_source":"B-Rep internal cylindrical face"}],
                "slot_planar_side_candidates":[
                    {"origin_mm":[cx-10,cy-10,-20],"normal":[0,-1,0]},
                    {"origin_mm":[cx-10,cy+10,-20],"normal":[0,1,0]}]}}


def test_b004_contract_preserves_position_through_graph_and_plan():
    source=graph(); features=infer_feature_graph(source); plan=build_plan(features)
    slot=features.slots[0]; operation=plan.operations[-1]
    assert validate_projection(source)["status"] == features.status == "PASS"
    assert (slot.center_x_mm,slot.center_y_mm)==(15,8)
    assert (operation.profile["center_x_mm"],operation.profile["center_y_mm"])==(15,8)


def test_cross_view_x_conflict_is_input_inconsistent():
    source=graph(); source.top.hidden_line_pairs[0]=HiddenLinePair("x",42,82)
    assert validate_projection(source)["error_code"]=="INPUT_INCONSISTENT"


def test_cross_view_y_conflict_is_input_inconsistent():
    source=graph(); source.left.hidden_line_pairs[0]=HiddenLinePair("y",25,45)
    assert validate_projection(source)["error_code"]=="INPUT_INCONSISTENT"


def test_missing_cross_view_position_evidence_is_ambiguous():
    source=graph(); source.top.hidden_line_pairs=[]
    assert infer_feature_graph(source).status=="AMBIGUOUS"


def test_translated_slot_crossing_base_boundary_is_input_inconsistent():
    source=graph()
    source.front.visible_segments[-2:]=[type(line)(line.x1+25,line.y1,line.x2+25,line.y2) for line in source.front.visible_segments[-2:]]
    source.front.arcs=[type(arc)(arc.x+25,arc.y,arc.radius,arc.start_angle_deg,arc.end_angle_deg,arc.sweep_direction) for arc in source.front.arcs]
    source.top.hidden_line_pairs[0]=HiddenLinePair("x",70,110)
    source.feature_evidence["straight_slot"]["expected"]["center_mm"]=[90,38]
    assert validate_projection(source)["error_code"]=="INPUT_INCONSISTENT"


def test_brep_x_offset_wrong_fails():
    source=graph(); features=infer_feature_graph(source)
    assert validate_reconstruction(features,backend_at(10,8))["status"]=="FAIL"


def test_brep_y_offset_wrong_fails():
    source=graph(); features=infer_feature_graph(source)
    assert validate_reconstruction(features,backend_at(15,5))["status"]=="FAIL"


def test_brep_mirror_and_recenter_regressions_fail():
    features=infer_feature_graph(graph())
    assert validate_reconstruction(features,backend_at(-15,8))["status"]=="FAIL"
    assert validate_reconstruction(features,backend_at(0,0))["status"]=="FAIL"


def test_level1_shape_correct_but_position_wrong_fails():
    source=graph(); features=infer_feature_graph(source)
    assert validate_level1(source,features,backend_at(0,0))["status"]=="FAIL"


def test_sheet_translation_does_not_change_feature_local_position():
    outer=[{"x1":100,"y1":200,"x2":200,"y2":200},{"x1":200,"y1":200,"x2":200,"y2":260},{"x1":200,"y1":260,"x2":100,"y2":260},{"x1":100,"y1":260,"x2":100,"y2":200}]
    slot=[{"x1":155,"y1":228,"x2":175,"y2":228},{"x1":175,"y1":248,"x2":155,"y2":248}]
    arcs=[{"x":155,"y":238,"radius":10,"start_angle_deg":90,"end_angle_deg":270,"sweep_direction":"CCW"},{"x":175,"y":238,"radius":10,"start_angle_deg":270,"end_angle_deg":90,"sweep_direction":"CCW"}]
    lines,_,mapped,_=normalize_geometry(outer+slot,[],arcs)
    assert lines[-1]["y1"]==48 and mapped[0]["x"]==55 and mapped[0]["y"]==38


def test_drawing_scale_does_not_change_canonical_slot_position():
    assert {to_view_local_mm((.065,.038),scale=value) for value in (1,.5,2)}=={(65,38)}


def test_translated_arc_segmentation_equivalent_but_wrong_position_fails():
    expected=[{"x":55,"y":38,"radius":10,"start_angle_deg":90,"end_angle_deg":270,"sweep_direction":"CCW"}]
    split=[{**expected[0],"end_angle_deg":180},{**expected[0],"start_angle_deg":180}]
    assert match_arc_supports(expected,split)["information"]==["GEOMETRY_EQUIVALENT","SEGMENTATION_DIFFERENT"]
    shifted=[{**expected[0],"x":50}]
    assert match_arc_supports(expected,shifted)["status"]=="FAIL"


def test_translated_line_shape_with_wrong_position_fails():
    expected=[{"x1":55,"y1":28,"x2":75,"y2":28}]
    actual=[{"x1":40,"y1":20,"x2":60,"y2":20}]
    assert match_line_supports(expected,actual)["status"]=="FAIL"


def test_b004_machine_readable_negative_suite_has_ten_expected_results():
    results=run_negative_tests(graph())
    assert len(results)==10
    assert all(item["expected"]==item["actual"] for item in results.values())
