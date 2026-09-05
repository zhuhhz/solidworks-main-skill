from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math


@dataclass(frozen=True)
class Circle:
    x: float
    y: float
    diameter: float
    primitive_id: str | None = None


@dataclass(frozen=True)
class HiddenLinePair:
    """Two hidden projection lines supporting a through feature candidate."""
    axis: str
    offset_1: float
    offset_2: float
    primitive_id: str | None = None


@dataclass(frozen=True)
class LineSegment:
    x1: float
    y1: float
    x2: float
    y2: float
    primitive_id: str | None = None


@dataclass(frozen=True)
class Arc:
    x: float
    y: float
    radius: float
    start_angle_deg: float
    end_angle_deg: float
    sweep_direction: str = "CCW"
    primitive_id: str | None = None

    def __post_init__(self):
        values = (self.x, self.y, self.radius, self.start_angle_deg, self.end_angle_deg)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("arc values must be finite")
        if self.radius <= 0:
            raise ValueError("arc radius must be positive")
        direction = self.sweep_direction.upper()
        if direction not in {"CW", "CCW"}:
            raise ValueError("arc sweep_direction must be CW or CCW")
        object.__setattr__(self, "start_angle_deg", float(self.start_angle_deg) % 360.0)
        object.__setattr__(self, "end_angle_deg", float(self.end_angle_deg) % 360.0)
        object.__setattr__(self, "sweep_direction", direction)
        if abs((self.end_angle_deg - self.start_angle_deg) % 360.0) < 1e-9:
            raise ValueError("Arc cannot represent a full circle or zero sweep")

    @property
    def sweep_deg(self) -> float:
        if self.sweep_direction == "CCW":
            return (self.end_angle_deg - self.start_angle_deg) % 360.0
        return (self.start_angle_deg - self.end_angle_deg) % 360.0


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
