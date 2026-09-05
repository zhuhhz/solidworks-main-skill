from __future__ import annotations

from dataclasses import asdict, dataclass, field


MODEL_COORDINATE_SYSTEM = "MODEL_CENTERED_XY_MM"


@dataclass(frozen=True)
class FeatureNode:
    """Backend-neutral identity/provenance view of one typed feature.

    The existing typed objects remain the parameter source.  This normalized
    view adds B005 identity and dependency semantics without replacing the
    B001-B004 schema.
    """

    feature_id: str
    feature_type: str
    parameters: dict
    source_evidence_ids: list[str]
    dependencies: list[str]
    coordinate_system: str = MODEL_COORDINATE_SYSTEM

    def to_dict(self) -> dict:
        return asdict(self)


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
    feature_id: str = "base_001"
    source_evidence_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    coordinate_system: str = MODEL_COORDINATE_SYSTEM

    def to_feature_node(self) -> FeatureNode:
        return FeatureNode(
            self.feature_id, "BASE_BLOCK",
            {"width_mm": self.width, "height_mm": self.height, "depth_mm": self.depth},
            list(self.source_evidence_ids), list(self.dependencies), self.coordinate_system,
        )


@dataclass
class Hole:
    diameter: float
    center_x: float
    center_y: float
    axis: str
    through: bool
    feature_id: str = "hole_001"
    source_evidence_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=lambda: ["base_001"])
    coordinate_system: str = MODEL_COORDINATE_SYSTEM

    def to_feature_node(self) -> FeatureNode:
        return FeatureNode(
            self.feature_id, "THROUGH_HOLE" if self.through else "HOLE",
            {"diameter_mm": self.diameter, "center_x_mm": self.center_x,
             "center_y_mm": self.center_y, "axis": self.axis, "through": self.through},
            list(self.source_evidence_ids), list(self.dependencies), self.coordinate_system,
        )


@dataclass
class Boss:
    width: float
    height: float
    depth: float
    centered: bool
    feature_id: str = "boss_001"
    source_evidence_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=lambda: ["base_001"])
    coordinate_system: str = MODEL_COORDINATE_SYSTEM

    def to_feature_node(self) -> FeatureNode:
        return FeatureNode(
            self.feature_id, "BOSS",
            {"width_mm": self.width, "height_mm": self.height, "depth_mm": self.depth,
             "centered": self.centered},
            list(self.source_evidence_ids), list(self.dependencies), self.coordinate_system,
        )


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
    feature_id: str = "slot_001"
    source_evidence_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=lambda: ["base_001"])
    coordinate_system: str = MODEL_COORDINATE_SYSTEM

    def to_feature_node(self) -> FeatureNode:
        return FeatureNode(
            self.feature_id, self.type,
            {"overall_length_mm": self.overall_length_mm, "width_mm": self.width_mm,
             "radius_mm": self.radius_mm, "center_x_mm": self.center_x_mm,
             "center_y_mm": self.center_y_mm, "major_axis": self.major_axis,
             "through": self.through},
            list(self.source_evidence_ids), list(self.dependencies), self.coordinate_system,
        )


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

    def to_feature_nodes(self) -> list[FeatureNode]:
        """Return deterministic Base/Boss/Hole/Slot normalized nodes."""
        values = [self.base_block, *self.bosses, *self.holes, *self.slots]
        return [value.to_feature_node() for value in values]
