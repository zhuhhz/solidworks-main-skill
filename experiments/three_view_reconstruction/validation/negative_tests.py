from __future__ import annotations
from copy import deepcopy
from inference.feature_hypothesis import infer_feature_graph
from validation.projection_consistency import validate

def run(graph):
    inconsistent = deepcopy(graph); inconsistent.top.horizontal_extent = 95
    insufficient_step = deepcopy(graph); insufficient_step.feature_evidence["centred_step"]["evidence"] = ["visible_step_in_front"]
    missing_hole = deepcopy(graph); missing_hole.top.hidden_line_pairs = []
    return {
        "dimension_mismatch": {"expected": "INPUT_INCONSISTENT", "actual": validate(inconsistent).get("error_code")},
        "boss_or_recess": {"expected": "AMBIGUOUS", "actual": infer_feature_graph(insufficient_step).status},
        "missing_hole_hidden_lines": {"expected": "AMBIGUOUS", "actual": infer_feature_graph(missing_hole).status},
    }
