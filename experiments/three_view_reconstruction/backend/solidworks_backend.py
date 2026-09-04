from __future__ import annotations

import os
import sys
from pathlib import Path

# The CAD execution layer is an explicit third-party dependency, never this
# experiment's source tree.  A missing value is an actionable integration gap.
_configured_upstream = os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH")
# The sibling checkout is the documented local-development integration target.
# An empty environment variable must never resolve to this repository's copied
# compatibility files (``Path(\"\") == .`` on Windows).
UPSTREAM_ROOT = Path(_configured_upstream) if _configured_upstream else Path(__file__).resolve().parents[4] / "solidworks-automation-skill"
if not (UPSTREAM_ROOT / "scripts" / "sw_session.py").is_file():
    raise RuntimeError("UPSTREAM_GAP: set SOLIDWORKS_AUTOMATION_BACKEND_PATH to the external solidworks-automation-skill clone")
sys.path.insert(0, str(UPSTREAM_ROOT / "scripts"))

from sw_connect import create_empty_dispatch_variant, get_com_member, mm
from sw_drawing import create_standard_views_with_projection, inspect_drawing_structure
from sw_hole_features import create_through_hole
from sw_part import extrude_boss, extrude_cut, sketch, sketch_rectangle, sketch_slot
from sw_review import collect_geometry_measurements, collect_model_summary, run_review
from sw_session import SolidWorksSession


def _select_front_plane(model) -> bool:
    """Locale-compatible counterpart of the upstream CNC helper."""
    for name in ("Front Plane", "前视基准面"):
        if model.Extension.SelectByID2(name, "PLANE", 0, 0, 0, False, 0, create_empty_dispatch_variant(), 0):
            return True
    return False


def _close_existing_target_documents(session, targets: tuple[Path, ...]) -> None:
    """Close only prior benchmark artefacts at exact known paths.

    This prevents a connected user-owned SolidWorks instance from holding a
    generated test drawing open across runs.  It never closes unrelated or
    unsaved user documents.
    """
    wanted = {str(path.resolve()).casefold() for path in targets}
    # The late-bound COM wrapper varies between pywin32 generated interfaces.
    # Close only the active document when its fully-qualified path is an exact
    # benchmark target.  This avoids relying on undocumented enumeration names
    # and is deliberately conservative around user documents.
    try:
        active = session.sw.ActiveDoc
        active_path = str(get_com_member(active, "GetPathName")) if active is not None else ""
        if active is not None and active_path.casefold() in wanted:
            session.sw.CloseDoc(str(get_com_member(active, "GetTitle")))
    except Exception:
        # A failed clean-up must not hide the actual modelling diagnostic.
        return


def _collect_slot_planar_sidewalls(model, plan) -> list[dict]:
    """Minimal adapter evidence absent from the external backend collector."""
    profiles = [op.profile for op in plan.operations if op.type == "cut_extrude_through_slot"]
    if not profiles:
        return []
    rows = []
    for body_index, body in enumerate(get_com_member(model, "GetBodies2", 0, False) or []):
        for face_index, face in enumerate(get_com_member(body, "GetFaces") or []):
            try:
                surface = get_com_member(face, "GetSurface")
                if not surface or not get_com_member(surface, "IsPlane"):
                    continue
                params = list(get_com_member(surface, "PlaneParams") or [])
                if len(params) < 6:
                    continue
                normal = [float(v) for v in params[:3]]
                origin = [float(v)*1000 for v in params[3:6]]
                for profile in profiles:
                    transverse = 1 if profile["major_axis"] == "X" else 0
                    coordinate = origin[transverse]
                    expected = profile["center_y_mm"] if transverse == 1 else profile["center_x_mm"]
                    if abs(abs(coordinate-expected)-profile["width_mm"]/2) <= .05 and abs(normal[transverse]) >= .99:
                        rows.append({"origin_mm": origin, "normal": normal,
                                     "area_mm2": float(get_com_member(face, "GetArea") or 0)*1_000_000,
                                     "internal": bool(get_com_member(face, "FaceInSurfaceSense")),
                                     "body_index": body_index, "face_index": face_index})
                        break
            except Exception:
                continue
    return rows


def execute(plan, output_dir: Path, name: str) -> dict:
    """Backend is intentionally thin: all CAD calls go through the existing Skill."""
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path, drawing_path = output_dir / f"{name}.sldprt", output_dir / f"{name}.slddrw"
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    part_title = drawing_title = None
    result = {"status": "FAIL", "skill_gaps": [], "operations": [],
              "external_backend_path": str(UPSTREAM_ROOT)}
    try:
        _close_existing_target_documents(session, (part_path, drawing_path))
        part = session.new_part(); part_title = str(get_com_member(part, "GetTitle"))
        for operation in plan.operations:
            if operation.type == "base_extrude":
                with sketch(part, operation.sketch_plane) as sketch_name:
                    sketch_rectangle(part, 0, 0, mm(operation.profile["width_mm"]), mm(operation.profile["height_mm"]))
                feature = extrude_boss(part, sketch_name, mm(operation.depth_mm))
                if feature is None: raise RuntimeError("SKILL_GAP: base_extrude returned None")
                feature.Name = "BaseBlock"
            elif operation.type == "boss_extrude":
                # Minimal compatibility supplement: the external backend has
                # plane/sketch/extrude helpers but no one-call stepped-boss API.
                # InsertRefPlane follows its tested CNC subskill convention.
                plane_name = operation.sketch_plane
                if part.FeatureByName(plane_name) is None:
                    selected = _select_front_plane(part)
                    if not selected:
                        raise RuntimeError("UPSTREAM_GAP: cannot select Front Plane for boss reference plane")
                    plane = part.FeatureManager.InsertRefPlane(8, mm(operation.profile["plane_offset_mm"]), 0, 0, 0, 0)
                    if plane is None:
                        raise RuntimeError("UPSTREAM_GAP: InsertRefPlane failed for stepped boss")
                    plane.Name = plane_name
                with sketch(part, plane_name) as sketch_name:
                    sketch_rectangle(part, 0, 0, mm(operation.profile["width_mm"]), mm(operation.profile["height_mm"]))
                feature = extrude_boss(part, sketch_name, mm(operation.depth_mm))
                if feature is None: raise RuntimeError("UPSTREAM_GAP: boss_extrude returned None")
                feature.Name = "TopBoss"
            elif operation.type == "cut_extrude_through_circle":
                plane_name = operation.sketch_plane
                if plane_name != "Front Plane" and part.FeatureByName(plane_name) is None:
                    selected = _select_front_plane(part)
                    if not selected:
                        raise RuntimeError("UPSTREAM_GAP: cannot select Front Plane for through-hole reference plane")
                    plane = part.FeatureManager.InsertRefPlane(8, mm(operation.profile["plane_offset_mm"]), 0, 0, 0, 0)
                    if plane is None:
                        raise RuntimeError("UPSTREAM_GAP: InsertRefPlane failed for through-hole plane")
                    plane.Name = plane_name
                evidence = create_through_hole(part, (mm(operation.profile["center_x_mm"]), mm(operation.profile["center_y_mm"])), mm(operation.profile["diameter_mm"]), plane_name=plane_name, name="ThroughHole_D20")
                result["operations"].append({"operation": operation.type, "evidence": evidence})
            elif operation.type == "cut_extrude_through_slot":
                profile = operation.profile
                radius = profile["width_mm"] / 2.0
                centre_distance = profile["overall_length_mm"] - 2.0 * radius
                if centre_distance <= 0:
                    raise ValueError("straight slot overall length must exceed its width")
                cx, cy = profile["center_x_mm"], profile["center_y_mm"]
                if profile["major_axis"] == "X":
                    start, end = (cx-centre_distance/2, cy), (cx+centre_distance/2, cy)
                else:
                    start, end = (cx, cy-centre_distance/2), (cx, cy+centre_distance/2)
                # UPSTREAM_GAP: create_semicircular_slot divides width by two,
                # but SW2024 CreateSketchSlot interprets this argument as the
                # end radius. Use the upstream sketch/extrude primitives with
                # corrected adapter semantics; do not patch/copy upstream.
                with sketch(part, operation.sketch_plane) as sketch_name:
                    # sketch_slot's final argument is forwarded as SW's slot
                    # width input despite its upstream name ``radius``.
                    segments = sketch_slot(part, mm(start[0]), mm(start[1]), mm(end[0]), mm(end[1]), mm(profile["width_mm"]))
                    if segments is None:
                        raise RuntimeError("UPSTREAM_GAP: sketch_slot returned None")
                    try:
                        active_sketch = get_com_member(part, "GetActiveSketch2")
                        sketch_segments = list(get_com_member(active_sketch, "GetSketchSegments") or [])
                        segment_rows = []
                        for item in sketch_segments:
                            try:
                                construction = bool(get_com_member(item, "ConstructionGeometry"))
                            except Exception:
                                construction = False
                            try:
                                segment_type = int(get_com_member(item, "GetType"))
                            except Exception:
                                segment_type = None
                            segment_rows.append({"type": segment_type, "construction": construction})
                        segment_count = len(sketch_segments)
                        profile_segment_count = sum(not row["construction"] for row in segment_rows)
                    except Exception:
                        segment_count = profile_segment_count = None; segment_rows = []
                feature = extrude_cut(part, sketch_name, 0.0)
                if feature is None:
                    raise RuntimeError("UPSTREAM_GAP: slot through-cut returned None")
                feature.Name = "ThroughSlot_L40_W20"
                evidence = {"feature_kind": "semicircular_slot", "start_mm": list(start), "end_mm": list(end),
                            "width_mm": profile["width_mm"], "depth_mm": None, "through": True,
                            "plane_name": operation.sketch_plane, "feature_names": ["ThroughSlot_L40_W20"],
                            "overall_length_mm": profile["overall_length_mm"], "center_to_center_length_mm": centre_distance,
                            "sketch_entity_count": segment_count, "profile_entity_count": profile_segment_count,
                            "sketch_entities": segment_rows, "profile_entity_contract": 4, "api_success": True,
                            "upstream_gap": "create_semicircular_slot width semantics produce half requested width on SW2024"}
                result["skill_gaps"].append("UPSTREAM_GAP: corrected create_semicircular_slot width semantics in adapter")
                result["operations"].append({"operation": operation.type, "evidence": evidence})
            else:
                raise RuntimeError(f"SKILL_GAP: unsupported plan operation {operation.type}")
        part.ForceRebuild3(False)
        if not session.save(part, str(part_path)): raise RuntimeError("SLDPRT save failed")
        result["model_summary"] = collect_model_summary(part)
        result["geometry"] = collect_geometry_measurements(part)
        result["geometry"]["slot_planar_side_candidates"] = _collect_slot_planar_sidewalls(part, plan)
        review, review_path = run_review(part, output_dir / "review", basename=name, expected_outputs=[part_path])
        result["review"] = {"path": str(review_path), "evaluation": review["evaluation"]}
        # Reopen is intentionally exercised before drawing generation.
        session.close(title=part_title); part = session.open(str(part_path), read_only=True, silent=True); part_title = str(get_com_member(part, "GetTitle"))
        result["reopened_model_summary"] = collect_model_summary(part)
        result["reopened_geometry"] = collect_geometry_measurements(part)
        result["reopened_geometry"]["slot_planar_side_candidates"] = _collect_slot_planar_sidewalls(part, plan)
        drawing = session.new_drawing(); drawing_title = str(get_com_member(drawing, "GetTitle"))
        result["drawing_create"] = create_standard_views_with_projection(drawing, str(part_path), projection="third_angle")
        if not session.save(drawing, str(drawing_path)): raise RuntimeError("SLDDRW save failed")
        result["drawing_structure"] = inspect_drawing_structure(drawing)
        result.update({"status": "PASS", "part_path": str(part_path), "drawing_path": str(drawing_path)})
    except Exception as exc:
        result.update({"status": "FAIL", "error": repr(exc)})
    finally:
        if drawing_title: session.close(title=drawing_title)
        if part_title: session.close(title=part_title)
        session.quit_owned_instance()
    return result
