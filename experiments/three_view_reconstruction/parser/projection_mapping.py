"""Single source of truth for orthographic coordinate correspondences."""
from __future__ import annotations

from drawing.view_orientation import CanonicalViewFrame


def validate_projection_name(projection: str) -> str:
    if projection not in {"first_angle", "third_angle"}:
        raise ValueError("projection 必须是 first_angle 或 third_angle")
    return projection


def front_to_internal(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> tuple[float, float]:
    """Input front-view lower-left coordinate -> model-centred X/Y."""
    return x_mm - width_mm / 2.0, y_mm - height_mm / 2.0


def internal_to_front(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> tuple[float, float]:
    return x_mm + width_mm / 2.0, y_mm + height_mm / 2.0


def correspondences() -> dict[str, str]:
    return {"front.x": "top.x", "front.y": "left.y", "top.z": "left.z"}


_INPUT_AXES = {
    "front": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),  # X / Y
    "top": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),    # X / Z
    "left": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),   # Z / Y
}


def _dot(left, right) -> float:
    return sum(a * b for a, b in zip(left, right))


def _world_point(role: str, x: float, y: float):
    axis_x, axis_y = _INPUT_AXES[role]
    return tuple(axis_x[index] * x + axis_y[index] * y for index in range(3))


def map_point_to_frame(role: str, x: float, y: float, width: float, height: float,
                       target: CanonicalViewFrame) -> tuple[float, float]:
    """Map input X/Y, X/Z, or Z/Y coordinates into a generated view frame."""
    corners = [_world_point(role, px, py) for px, py in ((0, 0), (width, 0), (0, height), (width, height))]
    min_u = min(_dot(point, target.right) for point in corners)
    min_v = min(_dot(point, target.up) for point in corners)
    world = _world_point(role, x, y)
    return _dot(world, target.right) - min_u, _dot(world, target.up) - min_v


def map_lines_to_frame(role: str, lines: list[dict], width: float, height: float,
                       target: CanonicalViewFrame) -> list[dict]:
    mapped = []
    for line in lines:
        p1 = map_point_to_frame(role, line["x1"], line["y1"], width, height, target)
        p2 = map_point_to_frame(role, line["x2"], line["y2"], width, height, target)
        mapped.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
    return mapped


def map_circles_to_frame(role: str, circles: list[dict], width: float, height: float,
                         target: CanonicalViewFrame) -> list[dict]:
    mapped = []
    for circle in circles:
        center = map_point_to_frame(role, circle["x"], circle["y"], width, height, target)
        mapped.append({"x": center[0], "y": center[1], "diameter": circle["diameter"]})
    return mapped
