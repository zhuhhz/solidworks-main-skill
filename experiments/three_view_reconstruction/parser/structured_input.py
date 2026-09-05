from __future__ import annotations

import json
from pathlib import Path

from schemas.projection_graph import ProjectionGraph
from schemas.feature_evidence import FeatureEvidence
from schemas.view_geometry import Arc, Circle, HiddenLinePair, LineSegment, ViewGeometry


def _view(name: str, data: dict) -> ViewGeometry:
    return ViewGeometry(
        name=name,
        horizontal_extent=float(data["horizontal_extent_mm"]),
        vertical_extent=float(data["vertical_extent_mm"]),
        circles=[Circle(**item) for item in data.get("circles", [])],
        hidden_line_pairs=[HiddenLinePair(**item) for item in data.get("hidden_line_pairs", [])],
        visible_segments=[LineSegment(**item) for item in data.get("visible_segments", [])],
        hidden_segments=[LineSegment(**item) for item in data.get("hidden_segments", [])],
        arcs=[Arc(**item) for item in data.get("arcs", [])],
        centerlines=[LineSegment(**item) for item in data.get("centerlines", [])],
    )


def load_structured_input(path: str | Path) -> ProjectionGraph:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") not in {"0.1", "0.2", "0.3", "0.4", "0.5"}:
        raise ValueError("只接受 schema_version=0.1、0.2、0.3、0.4 或 0.5 的结构化三视图输入")
    raw_evidence = raw.get("feature_evidence")
    legacy_evidence = raw_evidence if isinstance(raw_evidence, dict) else None
    evidence_records = [FeatureEvidence(**item) for item in raw_evidence] if isinstance(raw_evidence, list) else []
    return ProjectionGraph(
        projection=raw.get("projection", "third_angle"),
        front=_view("front", raw["front"]),
        top=_view("top", raw["top"]),
        left=_view("left", raw["left"]),
        coordinate_convention={
            "input": "mm; drawing lower-left origin",
            "front": "X/Y", "top": "X/Z", "left": "Z/Y",
            "internal": "mm; base-block centre origin; +Z is extrude direction",
        },
        feature_evidence=legacy_evidence,
        feature_evidence_records=evidence_records,
        expected_features=raw.get("expected_features"),
        center_requirements=raw.get("center_requirements", []),
        reference_integrity=raw.get("reference_integrity"),
    )
