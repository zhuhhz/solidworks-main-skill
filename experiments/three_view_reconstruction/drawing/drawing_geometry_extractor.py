"""Experimental projected-drawing geometry extractor.

UPSTREAM_GAP: the external backend has no projected-primitive reader.  This
small adapter uses actual SW2024 IView.GetPolyLinesAndCurves data, not B-Rep
edges.  It currently exposes visible projected polylines; hidden/centre line
classification remains unavailable from this API response and is reported as
such rather than inferred.
"""
from __future__ import annotations

import os, sys
from pathlib import Path
from win32com.client import gencache
from .view_coordinate_transform import to_view_local_mm, transform_metadata


DRAWING_DOC_CLSID = "{83A33D33-27C5-11CE-BFD4-00400513BB57}"


def _records(raw):
    i = 0
    while i + 9 <= len(raw):
        kind, geo_n = int(raw[i]), int(raw[i + 1]); i += 2
        geo = raw[i:i + geo_n]; i += geo_n
        attrs = raw[i:i + 6]; i += 6
        if i >= len(raw): break
        points_n = int(raw[i]); i += 1
        pts = raw[i:i + points_n * 3]; i += points_n * 3
        yield kind, geo, attrs, pts


def _line_or_circle(kind, pts, scale):
    points = [to_view_local_mm((float(pts[i]), float(pts[i + 1])), scale=scale) for i in range(0, len(pts) - 2, 3)]
    if len(points) == 2:
        return "line", {"x1": points[0][0], "y1": points[0][1], "x2": points[1][0], "y2": points[1][1]}
    # SW tessellates a projected circular edge.  Preserve it as a circle only
    # when all samples fit its bounding-box centre/radius within 0.02 mm.
    if kind == 1 and len(points) >= 8:
        xs, ys = zip(*points); cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        radius = (max(xs) - min(xs) + max(ys) - min(ys)) / 4
        if radius > 0 and max(abs(((x-cx)**2 + (y-cy)**2) ** .5 - radius) for x, y in points) <= .02:
            return "circle", {"x": cx, "y": cy, "diameter": 2 * radius}
    return "polyline", {"points": points}


def extract(drawing_path: str | Path) -> dict:
    upstream = Path(os.environ["SOLIDWORKS_AUTOMATION_BACKEND_PATH"])
    sys.path.insert(0, str(upstream / "scripts"))
    from sw_session import SolidWorksSession
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    model = session.open(str(drawing_path), read_only=True, silent=True)
    try:
        mod = gencache.GetModuleForCLSID(DRAWING_DOC_CLSID)
        doc = mod.IDrawingDoc(model._oleobj_)
        view = mod.IView(doc.GetFirstView()._oleobj_).GetNextView(); views = []
        while view is not None:
            v = mod.IView(view._oleobj_); ratio = list(v.ScaleRatio); scale = float(ratio[0]) / float(ratio[1])
            raw = list(v.GetPolyLinesAndCurves(0)); visible, circles, polylines = [], [], []
            for kind, _geo, _attrs, pts in _records(raw):
                category, payload = _line_or_circle(kind, pts, scale)
                if category == "line": visible.append(payload)
                elif category == "circle": circles.append(payload)
                else: polylines.append(payload)
            # Canonical origin is the projected geometry bounding-box lower-left,
            # not the sheet location or arbitrary model origin.
            xs = [p[k] for p in visible for k in ("x1", "x2")] + [c["x"] - c["diameter"] / 2 for c in circles]
            ys = [p[k] for p in visible for k in ("y1", "y2")] + [c["y"] - c["diameter"] / 2 for c in circles]
            dx, dy = (min(xs), min(ys)) if xs and ys else (0.0, 0.0)
            for p in visible:
                p["x1"] -= dx; p["x2"] -= dx; p["y1"] -= dy; p["y2"] -= dy
            for c in circles: c["x"] -= dx; c["y"] -= dy
            meta = transform_metadata(scale); meta["bounding_box_origin_removed_mm"] = [dx, dy]
            views.append({"name": str(v.Name), "scale": scale, "outline_m": list(v.GetOutline()), "position_m": list(v.Position), "visible_segments": visible, "hidden_segments": [], "circles": circles, "arcs": [], "centerlines": [], "unclassified_polylines": polylines, "transform": meta, "semantic_limitations": ["GetPolyLinesAndCurves returned no line-style/hidden classification in this SW2024 run", "centre marks are annotations, not model-edge polylines"]})
            view = v.GetNextView()
        return {"status": "PARTIAL", "api": "IView.GetPolyLinesAndCurves(0)", "coordinate_space": "view-local mm", "views": views, "capability_gap": "hidden/centre-line semantic extraction not demonstrated"}
    finally:
        session.close(model=model); session.quit_owned_instance()
