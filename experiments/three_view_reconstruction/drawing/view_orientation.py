"""Canonical, name-independent drawing-view frames."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import TypeAlias

Vector3: TypeAlias = tuple[float, float, float]


class CanonicalViewOrientation(str, Enum):
    FRONT = "FRONT"; BACK = "BACK"; LEFT = "LEFT"; RIGHT = "RIGHT"; TOP = "TOP"; BOTTOM = "BOTTOM"


def cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


@dataclass(frozen=True)
class CanonicalViewFrame:
    """World-space basis for a drawing view; ``right = up × normal``."""

    normal: Vector3
    up: Vector3
    right: Vector3
    projection_type: str
    mirror_state: bool
    rotation_deg: float
    source_view_name: str
    canonical_role: CanonicalViewOrientation

    def __post_init__(self) -> None:
        if cross(self.up, self.normal) != self.right:
            raise ValueError("CanonicalViewFrame invariant violated: right != up × normal")

    # Compatibility properties for persisted v0.2 evidence consumers.
    @property
    def orientation(self) -> CanonicalViewOrientation: return self.canonical_role
    @property
    def view_normal_world(self) -> Vector3: return self.normal
    @property
    def screen_v_world(self) -> Vector3: return self.up
    @property
    def screen_u_world(self) -> Vector3: return self.right
    @property
    def projection_standard(self) -> str: return self.projection_type
    @property
    def mirrored(self) -> bool: return self.mirror_state
    @property
    def source_solidworks_orientation(self) -> str: return self.source_view_name

    def to_dict(self) -> dict:
        data = asdict(self)
        data["canonical_role"] = self.canonical_role.value
        return data


# Backwards-compatible import name; new code should use CanonicalViewFrame.
ViewOrientationTransform = CanonicalViewFrame


_NORMAL_UP = {
    CanonicalViewOrientation.FRONT: ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    CanonicalViewOrientation.BACK: ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    CanonicalViewOrientation.RIGHT: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    CanonicalViewOrientation.LEFT: ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    CanonicalViewOrientation.TOP: ((0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
    CanonicalViewOrientation.BOTTOM: ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
}


def canonicalize(source: str, projection_standard: str = "THIRD_ANGLE", *,
                 mirrored: bool = False, rotation_deg: float = 0.0) -> CanonicalViewFrame:
    # GetOrientationName() is localized (for example ``*前视`` in a Chinese
    # SolidWorks installation).  Normalize only documented standard-view
    # aliases; an unknown orientation must remain an error, not be guessed.
    key = str(source).strip().upper().replace("*", "")
    aliases = {
        "FRONT": "FRONT", "前视": "FRONT", "前视图": "FRONT",
        "BACK": "BACK", "后视": "BACK", "后视图": "BACK",
        "RIGHT": "RIGHT", "右视": "RIGHT", "右视图": "RIGHT",
        "LEFT": "LEFT", "左视": "LEFT", "左视图": "LEFT",
        "TOP": "TOP", "上视": "TOP", "上视图": "TOP",
        "BOTTOM": "BOTTOM", "下视": "BOTTOM", "下视图": "BOTTOM",
    }
    key = aliases.get(key, key)
    orientation = CanonicalViewOrientation(key)
    normal, up = _NORMAL_UP[orientation]
    return CanonicalViewFrame(
        normal=normal,
        up=up,
        right=cross(up, normal),
        projection_type=projection_standard.upper(),
        mirror_state=mirrored,
        rotation_deg=float(rotation_deg),
        source_view_name=str(source),
        canonical_role=orientation,
    )


def comparable(generated: CanonicalViewFrame, requested: CanonicalViewFrame) -> bool:
    """Views are directly comparable only when their screen frames agree."""
    return (
        generated.normal, generated.up, generated.right,
        generated.mirror_state, generated.rotation_deg,
    ) == (
        requested.normal, requested.up, requested.right,
        requested.mirror_state, requested.rotation_deg,
    )
