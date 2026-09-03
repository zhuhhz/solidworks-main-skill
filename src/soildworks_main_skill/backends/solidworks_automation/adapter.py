"""Adapter boundary for the third-party SolidWorks automation backend.

No third-party implementation is copied here. Backend loading is deliberately
explicit so an unavailable checkout becomes an auditable UPSTREAM_GAP.
"""
from __future__ import annotations

from .capabilities import UpstreamGap
from .compatibility import external_backend_path


def availability() -> dict:
    path = external_backend_path()
    if path is None:
        return UpstreamGap(
            operation="solidworks_backend",
            reason="SOLIDWORKS_AUTOMATION_BACKEND_PATH is not configured to an external upstream checkout",
        ).to_dict()
    return {"status": "AVAILABLE", "backend_path": str(path)}
