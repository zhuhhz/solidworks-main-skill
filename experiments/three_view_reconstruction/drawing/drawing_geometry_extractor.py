"""Experimental projected-drawing geometry extractor.

UPSTREAM_GAP: the external backend has no projected-primitive reader.  This
small adapter uses actual SW2024 IView.GetPolyLinesAndCurves data, not B-Rep
edges.  It currently exposes visible projected polylines; hidden/centre line
classification remains unavailable from this API response and is reported as
such rather than inferred.
"""
from __future__ import annotations

import math, os, sys
from pathlib import Path
from win32com.client import gencache
from .view_coordinate_transform import normalize_geometry, to_view_local_mm, transform_metadata
from .view_orientation import canonicalize


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


def _line_or_circle(kind, pts, scale, geo=None):
    points = [to_view_local_mm((float(pts[i]), float(pts[i + 1])), scale=scale) for i in range(0, len(pts) - 2, 3)]
    if len(points) == 2:
        return "line", {"x1": points[0][0], "y1": points[0][1], "x2": points[1][0], "y2": points[1][1]}
    # Type-1 geometry exposes centre/start/end/normal. Tessellation order gives
    # the sweep direction without guessing from the expected reference.
    if kind == 1 and len(points) >= 8:
        if geo is not None and len(geo) >= 9:
            cx, cy = to_view_local_mm((float(geo[0]), float(geo[1])), scale=scale)
        else:
            xs, ys = zip(*points); cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        radii = [math.hypot(x-cx, y-cy) for x, y in points]
        radius = sum(radii)/len(radii)
        if radius > 0 and max(abs(value-radius) for value in radii) <= .05:
            if math.dist(points[0], points[-1]) <= .02:
                return "circle", {"x": cx, "y": cy, "diameter": 2 * radius}
            angles = [math.degrees(math.atan2(y-cy, x-cx)) % 360 for x, y in points]
            signed = sum(((b-a+180) % 360)-180 for a, b in zip(angles, angles[1:]))
            return "arc", {"x": cx, "y": cy, "radius": radius,
                           "start_angle_deg": angles[0], "end_angle_deg": angles[-1],
                           "sweep_direction": "CCW" if signed >= 0 else "CW"}
    return "polyline", {"points": points}


def extract(drawing_path: str | Path, *, upstream_path: str | Path | None = None,
            drawing_structure: dict | None = None) -> dict:
    """Read generated drawing primitives.

    ``upstream_path`` is explicit because the adapter can be invoked after the
    backend process/environment was configured.  Environment lookup remains a
    convenience for standalone diagnostics only.
    """
    upstream = Path(upstream_path or os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH", ""))
    if not (upstream / "scripts" / "sw_session.py").is_file():
        raise RuntimeError("UPSTREAM_GAP: external backend path was not supplied")
    sys.path.insert(0, str(upstream / "scripts"))
    from sw_session import SolidWorksSession
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    model = session.open(str(drawing_path), read_only=True, silent=True)
    try:
        mod = gencache.GetModuleForCLSID(DRAWING_DOC_CLSID)
        doc = mod.IDrawingDoc(model._oleobj_)
        view = mod.IView(doc.GetFirstView()._oleobj_).GetNextView(); views = []
        declared_views = (drawing_structure or {}).get("views", [])
        while view is not None:
            v = mod.IView(view._oleobj_); ratio = list(v.ScaleRatio); scale = float(ratio[0]) / float(ratio[1])
            raw = list(v.GetPolyLinesAndCurves(0)); visible, circles, arcs, polylines = [], [], [], []
            for kind, geo, _attrs, pts in _records(raw):
                category, payload = _line_or_circle(kind, pts, scale, geo)
                if category == "line": visible.append(payload)
                elif category == "circle": circles.append(payload)
                elif category == "arc": arcs.append(payload)
                else: polylines.append(payload)
            # Canonical origin is the projected geometry bounding-box lower-left,
            # not the sheet location or arbitrary model origin.
            visible, circles, arcs, (dx, dy) = normalize_geometry(visible, circles, arcs)
            meta = transform_metadata(scale); meta["bounding_box_origin_removed_mm"] = [dx, dy]
            declared = declared_views[len(views)] if len(views) < len(declared_views) else {}
            semantic_view = declared.get("semantic_view")
            try:
                raw_orientation = str(v.GetOrientationName())
                # Projected views report an empty GetOrientationName in the
                # tested SW2024 wrapper.  The drawing creator records their
                # deterministic standard-view role, which is stronger evidence
                # than their localized generated names.
                if not raw_orientation and semantic_view:
                    raw_orientation = semantic_view
                orientation = canonicalize(raw_orientation).to_dict()
                if semantic_view and not str(v.GetOrientationName()):
                    orientation["source"] = "drawing_structure.semantic_view"
            except Exception as exc:
                orientation = {"status": "UNKNOWN", "reason": repr(exc)}
            views.append({"name": str(v.Name), "semantic_view": semantic_view, "scale": scale, "outline_m": list(v.GetOutline()), "position_m": list(v.Position), "visible_segments": visible, "hidden_segments": [], "circles": circles, "arcs": arcs, "centerlines": [], "unclassified_polylines": polylines, "transform": meta, "orientation": orientation, "semantic_limitations": ["GetPolyLinesAndCurves returned no line-style/hidden classification in this SW2024 run", "centre marks are annotations, not model-edge polylines"]})
            view = v.GetNextView()
        return {"status": "PARTIAL", "api": "IView.GetPolyLinesAndCurves(0)", "coordinate_space": "view-local mm", "views": views, "capability_gap": "hidden/centre-line semantic extraction not demonstrated"}
    finally:
        session.close(model=model); session.quit_owned_instance()
