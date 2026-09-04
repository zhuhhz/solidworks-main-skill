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
class Boss:
    width: float
    height: float
    depth: float
    centered: bool


@dataclass
class StraightSlot:
    """Straight slot; overall length is end-to-end, not centre distance."""
    overall_length_mm: float
    width_mm: float
    radius_mm: float
    center_x_mm: float
    center_y_mm: float
    major_axis: str
    through: bool
    type: str = "STRAIGHT_SLOT"


@dataclass
class FeatureGraph:
    base_block: BaseBlock
    holes: list[Hole] = field(default_factory=list)
    bosses: list[Boss] = field(default_factory=list)
    slots: list[StraightSlot] = field(default_factory=list)
    hypotheses: list[FeatureHypothesis] = field(default_factory=list)
    status: str = "PASS"

    def to_dict(self) -> dict:
        return asdict(self)
