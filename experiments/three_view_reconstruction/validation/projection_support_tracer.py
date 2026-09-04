"""Trace drawing supports back to SolidWorks model topology.

This is an experimental compatibility layer, not a replacement for the
external automation backend.  ``IView.GetPolylines7`` supplies one model edge
or silhouette-edge object per returned drawing polyline.  For ordinary model
edges we follow that object to its vertices, adjacent faces, and the oldest
owning feature reported by ``IFace2.GetFeature``.

The tracer never invents correspondence: an API-backed row is ``EXACT``;
geometric-only matches are ``TOPOLOGY_INFERENCE``; failed casts remain
``UNRESOLVED``.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from win32com.client import gencache

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from drawing.drawing_geometry_extractor import _line_or_circle, _records
from drawing.view_coordinate_transform import normalize_primitives


DRAWING_DOC_CLSID = "{83A33D33-27C5-11CE-BFD4-00400513BB57}"
_TOLERANCE_MM = 0.10


def _member(value, name, *args):
    member = getattr(value, name)
    return member(*args) if callable(member) else member


def _point(vertex) -> list[float] | None:
    if vertex is None:
        return None
    return [round(float(value) * 1000.0, 6) for value in _member(vertex, "GetPoint")]


def _feature_name(face) -> str | None:
    feature = _member(face, "GetFeature")
    if feature is None:
        return None
    try:
        return str(_member(feature, "Name"))
    except Exception:
        return None


def _edge_topology(entity, module) -> dict:
    try:
        edge = module.IEdge(entity._oleobj_)
        adjacent = []
        for face_value in _member(edge, "GetTwoAdjacentFaces2") or ():
            if face_value is None:
                continue
            face = module.IFace2(face_value._oleobj_)
            adjacent.append({
                "face_id": int(_member(face, "GetFaceId")),
                "bounding_box_mm": [round(float(v) * 1000.0, 6) for v in _member(face, "GetBox")],
                "owning_feature": _feature_name(face),
            })
        owners = sorted({row["owning_feature"] for row in adjacent if row["owning_feature"]})
        return {
            "correspondence": "EXACT",
            "source_edge": {
                "edge_id": int(_member(edge, "GetID")),
                "start_mm": _point(_member(edge, "GetStartVertex")),
                "end_mm": _point(_member(edge, "GetEndVertex")),
            },
            "adjacent_faces": adjacent,
            "owning_features": owners,
        }
    except Exception as exc:
        return {
            "correspondence": "UNRESOLVED",
            "source_edge": None,
            "adjacent_faces": [],
            "owning_features": [],
            "reason": repr(exc),
        }


def _on_support(line: dict, target: dict) -> bool:
    ax, ay, bx, by = (float(line[k]) for k in ("x1", "y1", "x2", "y2"))
    tx1, ty1, tx2, ty2 = (float(target[k]) for k in ("x1", "y1", "x2", "y2"))
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return False
    cross_1 = abs(dx * (ty1 - ay) - dy * (tx1 - ax)) / length
    cross_2 = abs(dx * (ty2 - ay) - dy * (tx2 - ax)) / length
    if max(cross_1, cross_2) > _TOLERANCE_MM:
        return False
    ux, uy = dx / length, dy / length
    line_interval = sorted((ax * ux + ay * uy, bx * ux + by * uy))
    target_interval = sorted((tx1 * ux + ty1 * uy, tx2 * ux + ty2 * uy))
    return target_interval[0] >= line_interval[0] - _TOLERANCE_MM and target_interval[1] <= line_interval[1] + _TOLERANCE_MM


class ProjectionSupportTracer:
    """Audit explicit local-mm supports in a generated drawing."""

    def __init__(self, drawing_path: str | Path, *, upstream_path: str | Path):
        self.drawing_path = Path(drawing_path).resolve()
        self.upstream_path = Path(upstream_path).resolve()

    def trace(self, targets: list[dict]) -> dict:
        scripts = self.upstream_path / "scripts"
        if not (scripts / "sw_session.py").is_file():
            raise RuntimeError("UPSTREAM_GAP: external SolidWorks backend is unavailable")
        sys.path.insert(0, str(scripts))
        from sw_session import SolidWorksSession

        session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
        model = session.open(str(self.drawing_path), read_only=True, silent=True)
        rows = []
        try:
            module = gencache.GetModuleForCLSID(DRAWING_DOC_CLSID)
            drawing = module.IDrawingDoc(model._oleobj_)
            view = module.IView(drawing.GetFirstView()._oleobj_).GetNextView()
            view_index = 0
            while view is not None:
                wrapped = module.IView(view._oleobj_)
                ratio = list(wrapped.ScaleRatio)
                scale = float(ratio[0]) / float(ratio[1])
                entities, raw = wrapped.GetPolylines7(1)
                records = list(_records(list(raw)))
                line_rows, circles = [], []
                for index, (kind, _geo, attrs, points) in enumerate(records):
                    category, geometry = _line_or_circle(kind, points, scale)
                    if category == "line":
                        line_rows.append({"record_index": index, "geometry": geometry, "line_attributes": list(attrs)})
                    elif category == "circle":
                        circles.append(geometry)
                normalized, _, (dx, dy) = normalize_primitives([row["geometry"] for row in line_rows], circles)
                for row, geometry in zip(line_rows, normalized):
                    row["geometry"] = geometry

                semantic_view = ("FRONT", "TOP", "RIGHT")[view_index] if view_index < 3 else f"VIEW_{view_index + 1}"
                for target in (item for item in targets if item["view"].upper() == semantic_view):
                    matches = [row for row in line_rows if _on_support(row["geometry"], target["support"])]
                    if not matches:
                        rows.append({**target, "correspondence": "UNRESOLVED", "reason": "NO_PROJECTED_POLYLINE_CONTAINS_TARGET_SUPPORT"})
                        continue
                    for match in matches:
                        entity = entities[match["record_index"]] if match["record_index"] < len(entities) else None
                        topology = _edge_topology(entity, module) if entity is not None else {
                            "correspondence": "UNRESOLVED", "source_edge": None,
                            "adjacent_faces": [], "owning_features": [],
                            "reason": "GETPOLYLINES7_ENTITY_ARRAY_SHORTER_THAN_RECORD_ARRAY",
                        }
                        rows.append({
                            **target,
                            "drawing_view_name": str(wrapped.Name),
                            "projected_model_edge": match["geometry"],
                            "support_length_mm": round(math.dist(
                                (target["support"]["x1"], target["support"]["y1"]),
                                (target["support"]["x2"], target["support"]["y2"]),
                            ), 6),
                            "support_direction": "HORIZONTAL" if abs(target["support"]["y2"] - target["support"]["y1"]) <= _TOLERANCE_MM else "VERTICAL",
                            "semantic": "VISIBLE",
                            "provenance": "HLR_CAPTURE_GETPOLYLINES7",
                            "normalization_origin_mm": [dx, dy],
                            **topology,
                        })
                view_index += 1
                view = wrapped.GetNextView()
        finally:
            session.close(model=model)
            session.quit_owned_instance()
        status = "PASS" if rows and all(row.get("correspondence") == "EXACT" for row in rows) else "PARTIAL"
        return {
            "status": status,
            "api": "IView.GetPolylines7(1)",
            "drawing_path": str(self.drawing_path),
            "traces": rows,
        }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("drawing")
    parser.add_argument("--upstream", default=os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH", ""))
    parser.add_argument("--output")
    args = parser.parse_args()
    targets = [
        {"id": "B002_TOP_OVERFLOW_60", "view": "TOP", "support": {"x1": 20.0, "y1": 20.0, "x2": 80.0, "y2": 20.0}},
        {"id": "B002_RIGHT_OVERFLOW_40", "view": "RIGHT", "support": {"x1": 20.0, "y1": 10.0, "x2": 20.0, "y2": 50.0}},
    ]
    result = ProjectionSupportTracer(args.drawing, upstream_path=args.upstream).trace(targets)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
