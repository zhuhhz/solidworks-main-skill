from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class FeatureHypothesis:
    feature_type: str
    confidence: float
    evidence: list[str]
    status: str = "CONFIRMED"


@dataclass
class BaseBlock:
    width: float
    height: float
    depth: float


@dataclass
class Hole:
    diameter: float
    center_x: float
    center_y: float
    axis: str
    through: bool


@dataclass
class FeatureGraph:
    base_block: BaseBlock
    holes: list[Hole] = field(default_factory=list)
    hypotheses: list[FeatureHypothesis] = field(default_factory=list)
    status: str = "PASS"

    def to_dict(self) -> dict:
        return asdict(self)
