"""Backend-neutral ownership evidence contract for B005.

This module models evidence only.  It does not call SolidWorks and never turns
a localized feature name into ownership proof.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


OWNERSHIP_STRENGTHS = {
    "API_EXACT",
    "BREP_GEOMETRY_CORRELATED",
    "OWNERSHIP_UNRESOLVED",
}


@dataclass(frozen=True)
class OwnershipEvidence:
    entity_id: str
    entity_kind: str
    feature_id: str | None
    source: str
    strength: str
    details: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("ownership entity_id is required")
        if not self.entity_kind:
            raise ValueError("ownership entity_kind is required")
        if self.strength not in OWNERSHIP_STRENGTHS:
            raise ValueError(f"unsupported ownership strength: {self.strength}")
        if self.strength == "OWNERSHIP_UNRESOLVED" and self.feature_id is not None:
            raise ValueError("unresolved ownership cannot claim a feature_id")
        if self.strength != "OWNERSHIP_UNRESOLVED" and not self.feature_id:
            raise ValueError("resolved ownership requires a feature_id")

    def to_dict(self) -> dict:
        return asdict(self)
