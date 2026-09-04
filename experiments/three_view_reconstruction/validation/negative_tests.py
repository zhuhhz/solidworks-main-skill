from __future__ import annotations
from copy import deepcopy
from inference.feature_hypothesis import infer_feature_graph
from validation.projection_consistency import validate
from schemas.view_geometry import Arc, HiddenLinePair, LineSegment
from validation.primitive_matcher import match_arc_supports

def run(graph):
    if (graph.feature_evidence or {}).get("straight_slot"):
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
