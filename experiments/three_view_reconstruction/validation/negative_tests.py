from __future__ import annotations
from copy import deepcopy
from inference.feature_hypothesis import infer_feature_graph
from validation.projection_consistency import validate
from schemas.view_geometry import Arc, HiddenLinePair, LineSegment
from validation.primitive_matcher import match_arc_supports
from validation.primitive_matcher import match_line_supports
from drawing.view_coordinate_transform import normalize_geometry, to_view_local_mm

def run(graph):
    if (graph.feature_evidence or {}).get("straight_slot"):
        declared_center = graph.feature_evidence["straight_slot"].get("expected", {}).get("center_mm", [])
        if declared_center and declared_center != [graph.front.horizontal_extent/2, graph.front.vertical_extent/2]:
            cross_x = deepcopy(graph); cross_x.top.hidden_line_pairs[0]=HiddenLinePair("x",40,80)
            cross_y = deepcopy(graph); cross_y.left.hidden_line_pairs[0]=HiddenLinePair("y",25,45)
            declared_x = deepcopy(graph); declared_x.feature_evidence["straight_slot"]["expected"]["center_mm"]=[60,38]
            declared_y = deepcopy(graph); declared_y.feature_evidence["straight_slot"]["expected"]["center_mm"]=[65,35]
            expected_arcs=[arc.__dict__ for arc in graph.front.arcs]
            mirror_arcs=[{**arc,"x":arc["x"]-30} for arc in expected_arcs]
            centered_arcs=[{**arc,"x":arc["x"]-15,"y":arc["y"]-8} for arc in expected_arcs]
            split=[{**expected_arcs[0],"end_angle_deg":180},{**expected_arcs[0],"start_angle_deg":180},expected_arcs[1]]
            expected_lines=[line.__dict__ for line in graph.front.visible_segments[-2:]]
            centered_lines=[{**line,"x1":line["x1"]-15,"x2":line["x2"]-15,"y1":line["y1"]-8,"y2":line["y2"]-8} for line in expected_lines]
            translated_outer=[{"x1":100,"y1":200,"x2":200,"y2":200},{"x1":200,"y1":200,"x2":200,"y2":260},{"x1":200,"y1":260,"x2":100,"y2":260},{"x1":100,"y1":260,"x2":100,"y2":200}]
            translated_slot=[{"x1":155,"y1":228,"x2":175,"y2":228},{"x1":175,"y1":248,"x2":155,"y2":248}]
            _,_,normalized_arcs,_=normalize_geometry(translated_outer+translated_slot,[],[
                {"x":155,"y":238,"radius":10,"start_angle_deg":90,"end_angle_deg":270,"sweep_direction":"CCW"},
                {"x":175,"y":238,"radius":10,"start_angle_deg":270,"end_angle_deg":90,"sweep_direction":"CCW"}])
            scale_positions={to_view_local_mm((.065,.038),scale=value) for value in (1,.5,2)}
            return {
                "x_offset_wrong": {"expected":"INPUT_INCONSISTENT","actual":validate(declared_x).get("error_code")},
                "y_offset_wrong": {"expected":"INPUT_INCONSISTENT","actual":validate(declared_y).get("error_code")},
                "mirror_position": {"expected":"FAIL","actual":match_arc_supports(expected_arcs,mirror_arcs)["status"]},
                "recenter_regression": {"expected":"FAIL","actual":match_arc_supports(expected_arcs,centered_arcs)["status"]},
                "cross_view_x_conflict": {"expected":"INPUT_INCONSISTENT","actual":validate(cross_x).get("error_code")},
                "cross_view_y_conflict": {"expected":"INPUT_INCONSISTENT","actual":validate(cross_y).get("error_code")},
                "drawing_sheet_translation": {"expected":"PASS","actual":"PASS" if [(a["x"],a["y"]) for a in normalized_arcs]==[(55,38),(75,38)] else "FAIL"},
                "drawing_scale_invariance": {"expected":"PASS","actual":"PASS" if scale_positions=={(65,38)} else "FAIL"},
                "segmentation_different": {"expected":"PASS","actual":match_arc_supports(expected_arcs,split)["status"]},
                "shape_correct_position_wrong": {"expected":"FAIL","actual":match_line_supports(expected_lines,centered_lines)["status"]},
            }
        one_view = deepcopy(graph); one_view.top.hidden_line_pairs=[]; one_view.left.hidden_line_pairs=[]
        conflict = deepcopy(graph); conflict.left.hidden_line_pairs[0]=HiddenLinePair("y",21,39)
        radii = deepcopy(graph); radii.front.arcs[1]=Arc(60,30,9,270,90,"CCW")
        tangent = deepcopy(graph); tangent.front.visible_segments[-2]=LineSegment(40,20,60,21)
        opened = deepcopy(graph); opened.front.visible_segments.pop()
        blind = deepcopy(graph); blind.feature_evidence["straight_slot"].pop("through_state")
        wrong_center = deepcopy(graph); wrong_center.feature_evidence["straight_slot"]["expected"]["center_mm"]=[49,30]
        expected=[{"x":0,"y":0,"radius":10,"start_angle_deg":0,"end_angle_deg":180,"sweep_direction":"CCW"}]
        return {
            "single_view_missing_depth": {"expected":"AMBIGUOUS","actual":infer_feature_graph(one_view).status},
            "cross_view_width_conflict": {"expected":"INPUT_INCONSISTENT","actual":validate(conflict).get("error_code")},
            "end_arc_radius_mismatch": {"expected":"INPUT_INCONSISTENT","actual":validate(radii).get("error_code")},
            "line_arc_not_tangent": {"expected":"INPUT_INCONSISTENT","actual":validate(tangent).get("error_code")},
            "open_contour": {"expected":"INPUT_INCONSISTENT","actual":validate(opened).get("error_code")},
            "blind_vs_through": {"expected":"AMBIGUOUS","actual":infer_feature_graph(blind).status},
            "arc_split_equivalence": {"expected":"PASS", "actual":match_arc_supports(expected,[
                {**expected[0],"end_angle_deg":90},{**expected[0],"start_angle_deg":90}])["status"]},
            "angular_gap": {"expected":"FAIL","actual":match_arc_supports(expected,[{**expected[0],"end_angle_deg":89},{**expected[0],"start_angle_deg":90}])["status"]},
            "arc_overflow": {"expected":"FAIL","actual":match_arc_supports(expected,[{**expected[0],"start_angle_deg":355,"end_angle_deg":185}])["status"]},
            "wrong_slot_center": {"expected":"INPUT_INCONSISTENT","actual":validate(wrong_center).get("error_code")},
        }
    inconsistent = deepcopy(graph); inconsistent.top.horizontal_extent = 95
    insufficient_step = deepcopy(graph); insufficient_step.feature_evidence["centred_step"]["evidence"] = ["visible_step_in_front"]
    missing_hole = deepcopy(graph); missing_hole.top.hidden_line_pairs = []
    return {
        "dimension_mismatch": {"expected": "INPUT_INCONSISTENT", "actual": validate(inconsistent).get("error_code")},
        "boss_or_recess": {"expected": "AMBIGUOUS", "actual": infer_feature_graph(insufficient_step).status},
        "missing_hole_hidden_lines": {"expected": "AMBIGUOUS", "actual": infer_feature_graph(missing_hole).status},
    }
