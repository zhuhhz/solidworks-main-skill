from __future__ import annotations

from schemas.feature_graph import FeatureGraph
from schemas.projection_graph import ProjectionGraph
from .block_inference import infer_base_block
from .hole_inference import infer_holes
from .boss_inference import infer_bosses
from .slot_inference import infer_slots
from .evidence_binding import build_feature_graph_from_evidence


def infer_feature_graph(graph: ProjectionGraph) -> FeatureGraph:
    if graph.feature_evidence_records:
        features, _ = build_feature_graph_from_evidence(graph)
        return features
    holes, hypotheses = infer_holes(graph)
    bosses, boss_hypotheses = infer_bosses(graph)
    slots, slot_hypotheses = infer_slots(graph)
    hypotheses += boss_hypotheses + slot_hypotheses
    ambiguous = [h for h in hypotheses if h.status == "AMBIGUOUS"]
    failed = [h for h in hypotheses if h.status == "FAIL"]
    return FeatureGraph(base_block=infer_base_block(graph), holes=holes, bosses=bosses, slots=slots,
                        hypotheses=hypotheses, status="FAIL" if failed else "AMBIGUOUS" if ambiguous else "PASS")
