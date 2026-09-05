"""B006 projection evidence for pattern occurrences.

Attribution is explicit. Geometry coordinates validate a claimed occurrence;
they are never used to search for the nearest feature owner.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math


_VIEWS = {"front", "top", "left"}
_GEOMETRY_TYPES = {"CIRCLE", "HIDDEN_LINE"}


@dataclass(frozen=True)
class PatternEvidence:
    pattern_id: str
    seed_feature_id: str
    instance_id: str | None
    instance_index: int | None
    position: tuple[float, float, float] | None
    source_evidence_ids: tuple[str, ...]
    geometry_reference: str
    confidence: float
    view: str
    geometry_type: str
    source: str
    ownership_set: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.pattern_id or not self.seed_feature_id:
            raise ValueError("pattern_id and seed_feature_id are required")
        if not self.geometry_reference or not self.source:
            raise ValueError("geometry_reference and source are required")
        if self.view not in _VIEWS:
            raise ValueError(f"unsupported evidence view: {self.view}")
        geometry_type = self.geometry_type.upper()
        if geometry_type not in _GEOMETRY_TYPES:
            raise ValueError(f"unsupported pattern geometry_type: {self.geometry_type}")
        object.__setattr__(self, "geometry_type", geometry_type)
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be finite and between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        source_ids = tuple(self.source_evidence_ids)
        if not source_ids or any(not item for item in source_ids) or len(set(source_ids)) != len(source_ids):
            raise ValueError("source_evidence_ids must be nonempty and unique")
        object.__setattr__(self, "source_evidence_ids", source_ids)
        owners = tuple(self.ownership_set)
        if not owners or any(not item for item in owners) or len(set(owners)) != len(owners):
            raise ValueError("ownership_set must be nonempty and unique")
        object.__setattr__(self, "ownership_set", owners)

        shared = len(owners) > 1
        if shared:
            if self.instance_id is not None or self.instance_index is not None or self.position is not None:
                raise ValueError("overlapping evidence preserves an ownership_set and cannot claim one instance")
        else:
            if self.instance_id != owners[0] or type(self.instance_index) is not int:
                raise ValueError("single-owner evidence requires matching instance identity and integer index")
            if (not isinstance(self.position, (tuple, list)) or len(self.position) != 3
                    or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                               and math.isfinite(value) for value in self.position)):
                raise ValueError("single-owner evidence requires a finite 3D position")
            object.__setattr__(self, "position", tuple(float(value) for value in self.position))

    def to_dict(self) -> dict:
        return asdict(self)
