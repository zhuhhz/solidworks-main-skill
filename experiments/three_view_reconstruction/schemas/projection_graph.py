from __future__ import annotations

from dataclasses import asdict, dataclass
from .view_geometry import ViewGeometry


@dataclass
class ProjectionGraph:
    projection: str
    front: ViewGeometry
    top: ViewGeometry
    left: ViewGeometry
    coordinate_convention: dict
    feature_evidence: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)
