from __future__ import annotations

from schemas.feature_graph import FeatureHypothesis, Hole
from schemas.projection_graph import ProjectionGraph
from parser.projection_mapping import front_to_internal


def infer_holes(graph: ProjectionGraph) -> tuple[list[Hole], list[FeatureHypothesis]]:
    holes, hypotheses = [], []
    for circle in graph.front.circles:
        evidence = ["circle_in_front_view"]
        support = bool(graph.top.hidden_line_pairs) and bool(graph.left.hidden_line_pairs)
        if support:
            evidence += ["hidden_lines_in_top_view", "hidden_lines_in_left_view"]
            x, y = front_to_internal(circle.x, circle.y, graph.front.horizontal_extent, graph.front.vertical_extent)
            holes.append(Hole(circle.diameter, x, y, "Z", True))
            hypotheses.append(FeatureHypothesis("through_hole", 0.92, evidence))
        else:
            hypotheses.append(FeatureHypothesis("hole_or_cylindrical_boss", 0.45, evidence, "AMBIGUOUS"))
    return holes, hypotheses
