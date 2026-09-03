from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ModelingOperation:
    type: str
    sketch_plane: str
    profile: dict
    depth_mm: float | None = None
    direction: str | None = None


@dataclass
class ModelingPlan:
    operations: list[ModelingOperation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
