from __future__ import annotations

import json
from pathlib import Path

from schemas.projection_graph import ProjectionGraph
from schemas.view_geometry import Circle, HiddenLinePair, ViewGeometry


def _view(name: str, data: dict) -> ViewGeometry:
    return ViewGeometry(
        name=name,
        horizontal_extent=float(data["horizontal_extent_mm"]),
        vertical_extent=float(data["vertical_extent_mm"]),
        circles=[Circle(**item) for item in data.get("circles", [])],
        hidden_line_pairs=[HiddenLinePair(**item) for item in data.get("hidden_line_pairs", [])],
    )


def load_structured_input(path: str | Path) -> ProjectionGraph:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "0.1":
        raise ValueError("只接受 schema_version=0.1 的结构化三视图输入")
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
    )
