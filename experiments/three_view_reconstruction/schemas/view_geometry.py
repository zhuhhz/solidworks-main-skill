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


@dataclass(frozen=True)
class LineSegment:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class Arc:
    x: float
    y: float
    radius: float
    start_angle_deg: float
    end_angle_deg: float


@dataclass
class ViewGeometry:
    name: str
    horizontal_extent: float
    vertical_extent: float
    circles: list[Circle] = field(default_factory=list)
    hidden_line_pairs: list[HiddenLinePair] = field(default_factory=list)
    # Input-view-local millimetres: the Level-2 vector comparison contract.
    visible_segments: list[LineSegment] = field(default_factory=list)
    hidden_segments: list[LineSegment] = field(default_factory=list)
    arcs: list[Arc] = field(default_factory=list)
    centerlines: list[LineSegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
