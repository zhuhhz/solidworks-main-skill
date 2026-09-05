"""Structured-input evidence linking projection primitives to feature IDs.

The reference is explicit: this schema does not infer ownership from a
feature name, list order, or nearest geometry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math


VIEWS = {"front", "top", "left"}
GEOMETRY_TYPES = {"LINE", "HIDDEN_LINE", "HIDDEN_LINE_PAIR", "CIRCLE", "ARC", "CENTERLINE"}


@dataclass(frozen=True)
class FeatureEvidence:
    feature_id: str | None
    evidence_id: str
    view: str
    geometry_type: str
    geometry_reference: str
    confidence: float
    source: str

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if self.view not in VIEWS:
            raise ValueError(f"unsupported evidence view: {self.view}")
        geometry_type = self.geometry_type.upper()
        if geometry_type not in GEOMETRY_TYPES:
            raise ValueError(f"unsupported evidence geometry_type: {self.geometry_type}")
        object.__setattr__(self, "geometry_type", geometry_type)
        if not self.geometry_reference:
            raise ValueError("geometry_reference is required")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be finite and between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        if not self.source:
            raise ValueError("evidence source is required")

    def to_dict(self) -> dict:
        return asdict(self)
