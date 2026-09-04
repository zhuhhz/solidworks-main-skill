"""Controlled SolidWorks HLV/HLR projected-geometry differential probe."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from win32com.client import gencache

ROOT = Path(__file__).resolve().parents[2]
RECON = ROOT / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(RECON))

from drawing.drawing_geometry_extractor import DRAWING_DOC_CLSID, _line_or_circle, _records
from drawing.view_coordinate_transform import normalize_geometry, transform_metadata
from validation.primitive_matcher import match, match_line_supports, support_difference

SW_HLV = 1
SW_HLR = 2


def _upstream() -> Path:
    configured = os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH")
    path = Path(configured) if configured else ROOT.parent / "solidworks-automation-skill"
    if not (path / "scripts" / "sw_session.py").is_file():
        raise RuntimeError("UPSTREAM_GAP: external SolidWorks backend checkout not found")
    return path


def _typed_views(model):
    module = gencache.GetModuleForCLSID(DRAWING_DOC_CLSID)
    drawing = module.IDrawingDoc(model._oleobj_)
    view = module.IView(drawing.GetFirstView()._oleobj_).GetNextView()
    while view is not None:
        typed = module.IView(view._oleobj_)
        yield typed
        view = typed.GetNextView()


def _capture(model) -> list[dict]:
    rows = []
    for index, view in enumerate(_typed_views(model)):
        ratio = list(view.ScaleRatio)
        scale = float(ratio[0]) / float(ratio[1])
        lines, circles, arcs, polylines = [], [], [], []
        raw = list(view.GetPolyLinesAndCurves(0))
        for kind, geometry, _attributes, points in _records(raw):
            category, payload = _line_or_circle(kind, points, scale, geometry)
            if category == "line": lines.append(payload)
            elif category == "circle": circles.append(payload)
            elif category == "arc": arcs.append(payload)
            else: polylines.append(payload)
        lines, circles, arcs, origin = normalize_geometry(lines, circles, arcs)
        rows.append({
            "index": index, "name": str(view.Name), "scale": scale,
            "position_m": list(view.Position), "outline_m": list(view.GetOutline()),
            "lines": lines, "circles": circles, "arcs": arcs, "unclassified_polylines": polylines,
            "transform": transform_metadata(scale) | {"bounding_box_origin_removed_mm": list(origin)},
        })
    return rows


def _set_mode(model, mode: int) -> list[dict]:
    calls = []
    for index, view in enumerate(_typed_views(model)):
        returned = bool(view.SetDisplayMode3(False, mode, False, False))
        try:
            view.UpdateViewDisplayGeometry()
        except Exception as exc:
            calls.append({"index": index, "set_return": returned, "update_error": repr(exc)})
        else:
            calls.append({"index": index, "set_return": returned, "update_error": None})
    model.ForceRebuild3(False)
    return calls


def _mode_run(session, source: Path, target: Path, mode: int) -> dict:
    shutil.copy2(source, target)
    model = session.open(str(target), read_only=False, silent=True)
    try:
        before = {"position_m": [row["position_m"] for row in _capture(model)],
                  "scale": [row["scale"] for row in _capture(model)]}
        calls = _set_mode(model, mode)
        pre_save = _capture(model)
        saved = bool(session.save(model))
    finally:
        session.close(model=model)
    reopened = session.open(str(target), read_only=True, silent=True)
    try:
        post_reopen = _capture(reopened)
    finally:
        session.close(model=reopened)
    stability = []
    for first, second in zip(pre_save, post_reopen):
        stability.append({
            "view_index": first["index"],
            "lines": match_line_supports(first["lines"], second["lines"]),
            "circles": match(first["circles"], second["circles"], "circle"),
            "arcs": match(first["arcs"], second["arcs"], "arc"),
            "position_stable": first["position_m"] == second["position_m"],
            "scale_stable": first["scale"] == second["scale"],
        })
    return {"mode": mode, "set_calls": calls, "saved": saved, "initial_transform": before,
            "pre_save": pre_save, "post_reopen": post_reopen, "stability": stability,
            "status": "PASS" if saved and all(x["lines"]["status"] == "PASS" and x["circles"]["status"] == "PASS" and x["arcs"]["status"] == "PASS" and x["position_stable"] and x["scale_stable"] for x in stability) else "FAIL"}


def _differential(hlr: dict, hlv: dict) -> dict:
    views = []
    for removed, visible in zip(hlr["post_reopen"], hlv["post_reopen"]):
        diff = support_difference(removed["lines"], visible["lines"])
        hidden_circles = [circle for circle in visible["circles"] if match([], [circle], "circle")["status"] == "FAIL" and not any(match([circle], [base], "circle")["status"] == "PASS" for base in removed["circles"])]
        views.append({
            "view_index": removed["index"], "same_scale": removed["scale"] == visible["scale"],
            "same_sheet_location": removed["position_m"] == visible["position_m"],
            "visible_supports_stable": diff["visible_supports_stable"],
            "hidden_supports": diff["candidates"],
            "hidden_circles": [{"geometry_type": "CIRCLE", "semantic": "HIDDEN", "source": "HLV_MINUS_HLR", "confidence": 1.0, "geometry": item} for item in hidden_circles],
            "support_difference": diff,
        })
    reliable = all(v["same_scale"] and v["same_sheet_location"] and v["visible_supports_stable"] for v in views)
    has_hidden = any(v["hidden_supports"] or v["hidden_circles"] for v in views)
    return {"status": "PASS" if reliable and has_hidden else "PARTIAL",
            "semantic_provenance": "HLV_MINUS_HLR" if reliable and has_hidden else "SEMANTIC_PROVENANCE_UNAVAILABLE",
            "views": views}


def run_case(source: Path, case_name: str, output: Path) -> dict:
    """Run both display modes against one source drawing and persist evidence."""
    output.mkdir(parents=True, exist_ok=True)
    upstream = _upstream()
    sys.path.insert(0, str(upstream / "scripts"))
    from sw_session import SolidWorksSession
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    try:
        hlr = _mode_run(session, source, output / f"{case_name}_hlr.slddrw", SW_HLR)
        hlv = _mode_run(session, source, output / f"{case_name}_hlv.slddrw", SW_HLV)
    finally:
        session.quit_owned_instance()
    differential = _differential(hlr, hlv)
    report = {"case": case_name, "source_drawing": str(source),
              "run_at": datetime.now().isoformat(timespec="seconds"),
              "solidworks_api": {"method": "IView.SetDisplayMode3", "hlv": SW_HLV, "hlr": SW_HLR},
              "hlr": hlr, "hlv": hlv, "differential": differential,
              "status": "PASS" if hlr["status"] == hlv["status"] == differential["status"] == "PASS" else "PARTIAL"}
    (output / "hlr_geometry.json").write_text(json.dumps(hlr, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "hlv_geometry.json").write_text(json.dumps(hlv, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "semantic_diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, choices=("case_001_block_hole", "case_002_step_block"))
    args = parser.parse_args()
    source = RECON / "results" / args.case / f"{args.case}.slddrw"
    if not source.is_file():
        raise FileNotFoundError(source)
    output = Path(__file__).resolve().parent / "results" / args.case
    report = run_case(source, args.case, output)
    hlr, hlv, differential = report["hlr"], report["hlv"], report["differential"]
    print(json.dumps({"case": args.case, "status": report["status"], "hlr": hlr["status"], "hlv": hlv["status"], "differential": differential["status"], "provenance": differential["semantic_provenance"], "hidden_counts": [len(v["hidden_supports"]) + len(v["hidden_circles"]) for v in differential["views"]]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
