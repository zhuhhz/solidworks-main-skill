"""Loader for the bounded B006 structured pattern benchmark."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from parser.structured_input import _view
from schemas.feature_graph import BaseBlock
from schemas.pattern_evidence import PatternEvidence
from schemas.pattern_feature import InstanceFeature, PatternFeature, PatternFeatureGraph, SeedFeature
from schemas.projection_graph import ProjectionGraph


@dataclass(frozen=True)
class PatternStructuredInput:
    projection_graph: ProjectionGraph
    feature_graph: PatternFeatureGraph
    evidence: tuple[PatternEvidence, ...]


def load_pattern_structured_input(path: str | Path) -> PatternStructuredInput:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "0.6":
        raise ValueError("B006 pattern input requires schema_version=0.6")
    projection = ProjectionGraph(
        projection=raw.get("projection", "third_angle"),
        front=_view("front", raw["front"]),
        top=_view("top", raw["top"]),
        left=_view("left", raw["left"]),
        coordinate_convention={
            "input": "mm; drawing lower-left origin",
            "front": "X/Y", "top": "X/Z", "left": "Z/Y",
            "internal": "mm; base-block centre origin; +Z is extrude direction",
        },
    )
    data = raw["pattern_contract"]
    base_data, seed_data, pattern_data = data["base"], data["seed"], data["pattern"]
    base = BaseBlock(
        float(base_data["width_mm"]), float(base_data["height_mm"]), float(base_data["depth_mm"]),
        feature_id=base_data["feature_id"], dependencies=list(base_data.get("dependencies", [])),
    )
    seed = SeedFeature(
        seed_data["feature_id"], seed_data["pattern_id"], seed_data["source_feature_id"],
        tuple(seed_data["center_mm"]), float(seed_data["diameter_mm"]), list(seed_data["dependencies"]),
        axis=seed_data.get("axis", "Z"), through=seed_data.get("through", True),
    )
    pattern = PatternFeature(
        pattern_data["feature_id"], pattern_data["pattern_id"], pattern_data["source_feature_id"],
        float(pattern_data["spacing_mm"]), tuple(pattern_data["direction"]),
        pattern_data["total_count"], list(pattern_data["dependencies"]),
        includes_seed=pattern_data.get("includes_seed", True),
    )
    instances = [InstanceFeature(
        item["feature_id"], item["pattern_id"], item["source_feature_id"], item["instance_index"],
        tuple(item["center_mm"]), list(item["dependencies"]),
    ) for item in data["instances"]]
    evidence = tuple(PatternEvidence(
        pattern_id=item["pattern_id"], seed_feature_id=item["seed_feature_id"],
        instance_id=item.get("instance_id"), instance_index=item.get("instance_index"),
        position=tuple(item["position"]) if item.get("position") is not None else None,
        source_evidence_ids=tuple(item["source_evidence_ids"]),
        geometry_reference=item["geometry_reference"], confidence=item["confidence"],
        view=item["view"], geometry_type=item["geometry_type"], source=item["source"],
        ownership_set=tuple(item["ownership_set"]),
    ) for item in raw["pattern_evidence"])
    return PatternStructuredInput(projection, PatternFeatureGraph(base, seed, pattern, instances), evidence)
