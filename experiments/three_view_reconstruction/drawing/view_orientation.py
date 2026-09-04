"""Canonical, name-independent drawing-view orientation metadata.

The transform is intentionally explicit: a view label is evidence, not the
coordinate transform itself.  This module is pure Python so its rules can be
unit-tested without starting SolidWorks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class CanonicalViewOrientation(str, Enum):
    FRONT = "FRONT"; BACK = "BACK"; LEFT = "LEFT"; RIGHT = "RIGHT"; TOP = "TOP"; BOTTOM = "BOTTOM"


@dataclass(frozen=True)
class ViewOrientationTransform:
    orientation: CanonicalViewOrientation
    screen_u_world: str
    screen_v_world: str
    view_normal_world: str
    handedness: str = "RIGHT_HANDED"
    mirrored: bool = False
    rotation_deg: int = 0
    projection_standard: str = "THIRD_ANGLE"
    source_solidworks_orientation: str = ""

    def to_dict(self) -> dict: return asdict(self) | {"orientation": self.orientation.value}


_FRAMES = {
    CanonicalViewOrientation.FRONT: ("+X", "+Y", "+Z"),
    CanonicalViewOrientation.BACK: ("-X", "+Y", "-Z"),
    CanonicalViewOrientation.RIGHT: ("-Z", "+Y", "+X"),
    CanonicalViewOrientation.LEFT: ("+Z", "+Y", "-X"),
    CanonicalViewOrientation.TOP: ("+X", "-Z", "+Y"),
    CanonicalViewOrientation.BOTTOM: ("+X", "+Z", "-Y"),
}


def canonicalize(source: str, projection_standard: str = "THIRD_ANGLE") -> ViewOrientationTransform:
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
    u, v, normal = _FRAMES[orientation]
    return ViewOrientationTransform(orientation, u, v, normal, projection_standard=projection_standard, source_solidworks_orientation=str(source))


def comparable(generated: ViewOrientationTransform, requested: ViewOrientationTransform) -> bool:
    """Views are directly comparable only when their screen frames agree."""
    return (generated.screen_u_world, generated.screen_v_world, generated.view_normal_world) == (requested.screen_u_world, requested.screen_v_world, requested.view_normal_world)
