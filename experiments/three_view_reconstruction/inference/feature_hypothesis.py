from __future__ import annotations

from schemas.feature_graph import FeatureGraph
from schemas.projection_graph import ProjectionGraph
from .block_inference import infer_base_block
from .hole_inference import infer_holes
from .boss_inference import infer_bosses


def infer_feature_graph(graph: ProjectionGraph) -> FeatureGraph:
    holes, hypotheses = infer_holes(graph)
    bosses, boss_hypotheses = infer_bosses(graph)
    hypotheses += boss_hypotheses
    ambiguous = [h for h in hypotheses if h.status == "AMBIGUOUS"]
    return FeatureGraph(infer_base_block(graph), holes, bosses, hypotheses, "AMBIGUOUS" if ambiguous else "PASS")
