from __future__ import annotations

import os
from pathlib import Path


def external_backend_path() -> Path | None:
    value = os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH")
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    return path if path.is_dir() else None
