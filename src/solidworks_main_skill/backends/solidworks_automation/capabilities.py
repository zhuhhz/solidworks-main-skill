from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class UpstreamGap:
    operation: str
    reason: str
    upstream_version: str | None = None
    status: str = "UPSTREAM_GAP"

    def to_dict(self) -> dict:
        return asdict(self)
