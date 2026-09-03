from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from sw_connect import get_com_member, mm
from sw_drawing import create_standard_views_with_projection, inspect_drawing_structure
from sw_hole_features import create_through_hole
from sw_part import extrude_boss, sketch, sketch_rectangle
from sw_review import collect_geometry_measurements, collect_model_summary, run_review
from sw_session import SolidWorksSession


def execute(plan, output_dir: Path, name: str) -> dict:
    """Backend is intentionally thin: all CAD calls go through the existing Skill."""
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path, drawing_path = output_dir / f"{name}.sldprt", output_dir / f"{name}.slddrw"
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    part_title = drawing_title = None
    result = {"status": "FAIL", "skill_gaps": [], "operations": []}
    try:
        part = session.new_part(); part_title = str(get_com_member(part, "GetTitle"))
        for operation in plan.operations:
            if operation.type == "base_extrude":
                with sketch(part, operation.sketch_plane) as sketch_name:
                    sketch_rectangle(part, 0, 0, mm(operation.profile["width_mm"]), mm(operation.profile["height_mm"]))
                feature = extrude_boss(part, sketch_name, mm(operation.depth_mm))
                if feature is None: raise RuntimeError("SKILL_GAP: base_extrude returned None")
                feature.Name = "BaseBlock"
            elif operation.type == "cut_extrude_through_circle":
                evidence = create_through_hole(part, (mm(operation.profile["center_x_mm"]), mm(operation.profile["center_y_mm"])), mm(operation.profile["diameter_mm"]), name="ThroughHole_D20")
                result["operations"].append({"operation": operation.type, "evidence": evidence})
            else:
                raise RuntimeError(f"SKILL_GAP: unsupported plan operation {operation.type}")
        part.ForceRebuild3(False)
        if not session.save(part, str(part_path)): raise RuntimeError("SLDPRT save failed")
        result["model_summary"] = collect_model_summary(part)
        result["geometry"] = collect_geometry_measurements(part)
        review, review_path = run_review(part, output_dir / "review", basename=name, expected_outputs=[part_path])
        result["review"] = {"path": str(review_path), "evaluation": review["evaluation"]}
        # Reopen is intentionally exercised before drawing generation.
        session.close(title=part_title); part = session.open(str(part_path), read_only=True, silent=True); part_title = str(get_com_member(part, "GetTitle"))
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
