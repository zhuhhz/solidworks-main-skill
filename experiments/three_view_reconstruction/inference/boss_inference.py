from __future__ import annotations

from schemas.feature_graph import Boss, FeatureHypothesis
from schemas.projection_graph import ProjectionGraph


def infer_bosses(graph: ProjectionGraph) -> tuple[list[Boss], list[FeatureHypothesis]]:
    """Conservative multi-view rule for the centred stepped-block benchmark."""
    raw = graph.feature_evidence or {}
    step = raw.get("centred_step") if isinstance(raw, dict) else None
    if not step:
        return [], []
    evidence = list(step.get("evidence", []))
    required = {"visible_step_in_front", "reduced_width_in_top", "height_transition_in_left"}
    if not required.issubset(evidence):
        return [], [FeatureHypothesis("boss_or_recess", 0.45, evidence, "AMBIGUOUS")]
    return [Boss(float(step["width_mm"]), float(step["height_mm"]), float(step["depth_mm"]), bool(step.get("centered", True)))], [FeatureHypothesis("centred_boss", 0.88, evidence)]
