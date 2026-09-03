from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Circle:
    x: float
    y: float
    diameter: float


@dataclass(frozen=True)
class HiddenLinePair:
    """Two hidden projection lines supporting a through feature candidate."""
    axis: str
    offset_1: float
    offset_2: float


@dataclass
class ViewGeometry:
    name: str
    horizontal_extent: float
    vertical_extent: float
    circles: list[Circle] = field(default_factory=list)
    hidden_line_pairs: list[HiddenLinePair] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
