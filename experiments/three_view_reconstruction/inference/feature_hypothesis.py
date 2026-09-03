from __future__ import annotations

from schemas.feature_graph import FeatureGraph
from schemas.projection_graph import ProjectionGraph
from .block_inference import infer_base_block
from .hole_inference import infer_holes


def infer_feature_graph(graph: ProjectionGraph) -> FeatureGraph:
    holes, hypotheses = infer_holes(graph)
    ambiguous = [h for h in hypotheses if h.status == "AMBIGUOUS"]
    return FeatureGraph(infer_base_block(graph), holes, hypotheses, "AMBIGUOUS" if ambiguous else "PASS")
