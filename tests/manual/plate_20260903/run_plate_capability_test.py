"""独立人工测试：以仓库公开封装验证最小板件和 3D→2D 流程。

不修改 Skill 的生产代码；所有 CAD 操作均调用 scripts/ 或 subskills/ 的现有函数。
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "subskills" / "solidworks-fillet-chamfer-cnc" / "scripts"))

from sw_connect import get_com_member, mm
from sw_drawing import (add_section_view, auto_arrange_drawing_dimensions,
                        auto_insert_center_marks, create_adaptive_standard_views,
                        export_sheet_to_pdf, inspect_drawing_structure,
                        insert_dimensions, plan_standard_view_layout,
                        setup_current_sheet_as_a3)
from sw_export import export_to_dxf
from sw_hole_features import create_hole_pattern, create_through_hole
from sw_part import auto_dimension_sketch, chamfer, extrude_boss, sketch, sketch_rectangle
from sw_review import (collect_geometry_measurements, collect_model_summary,
                       run_review, validate_hole_positions)
from sw_session import SolidWorksSession
from create_cnc_mount_template import (all_edges, clear, edge_direction,
                                       edge_points, edge_signature, midpoint, select_exact_edges,
                                       vertical_corner_predicate)

OUT = Path(__file__).resolve().parent / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)


def call(result, label, func, *args, **kwargs):
    """记录每个公开 Skill 调用的返回值或完整异常。"""
    item = {"function": label, "inputs": {"args": [str(x) for x in args], "kwargs": kwargs}}
    try:
        value = func(*args, **kwargs)
        item["status"] = "pass" if value is not None and value is not False else "failed_return"
        item["return"] = str(value)
        result["calls"].append(item)
        return value
    except Exception as exc:
        item.update({"status": "exception", "exception": repr(exc), "traceback": traceback.format_exc()})
        result["calls"].append(item)
        return None


def _top_side_edge_predicate(edge):
    """借用 CNC 子技能的 B-Rep 语义工具：选圆角后 y=+30mm 的唯一顶边。"""
    pts = edge_points(edge)
    mid = midpoint(edge)
    tol = mm(0.05)
    return bool(
        pts and mid and edge_direction(edge) == "x"
        and all(abs(point[2]) <= tol for point in pts)
        and abs(mid[1] - mm(30)) <= tol
    )


def _drawing_templates():
    root = Path(r"D:\SW2024\SolidWorks2024\SOLIDWORKS")
    return [str(p) for p in root.rglob("*.slddrt") if "gb" in p.name.casefold() and "a4" in p.name.casefold()]


def run() -> dict:
    result = {"started": datetime.now().isoformat(timespec="seconds"), "calls": [], "failures": []}
    paths = {key: OUT / value for key, value in {
        "part": "plate_100x60x20.sldprt", "drawing": "plate_100x60x20.slddrw",
        "pdf": "plate_100x60x20.pdf", "dxf": "plate_100x60x20.dxf", "dwg": "plate_100x60x20.dwg",
    }.items()}
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    part_title = drawing_title = None
    try:
        result["solidworks"] = get_com_member(session.sw, "RevisionNumber")
        part = call(result, "SolidWorksSession.new_part", session.new_part)
        if part is None:
            raise RuntimeError("无法创建测试零件")
        part_title = str(get_com_member(part, "GetTitle"))
        with sketch(part, "Front Plane") as sketch_name:
            segments = sketch_rectangle(part, 0, 0, mm(100), mm(60))
            result["base_sketch_autodimension"] = call(result, "sw_part.auto_dimension_sketch", auto_dimension_sketch, part, sketch_segments=segments)
        boss = call(result, "sw_part.extrude_boss", extrude_boss, part, sketch_name, mm(20))
        if boss is None:
            raise RuntimeError("基础拉伸失败")
        try:
            boss.Name = "Base_100x60x20"
        except Exception:
            pass

        result["center_hole"] = call(result, "sw_hole_features.create_through_hole", create_through_hole, part, (0, 0), mm(20), name="ThroughHole_D20")
        corners = [(-40, -20), (-40, 20), (40, -20), (40, 20)]
        result["corner_holes"] = call(result, "sw_hole_features.create_hole_pattern", create_hole_pattern, part, [(mm(x), mm(y)) for x, y in corners], create_through_hole, diameter=mm(8), name="CornerHole_D8")

        # R5：用 CNC 子技能的精确边选择器，而非 Edge1/屏幕坐标。
        result["pre_fillet_edge_signatures"] = [edge_signature(edge) for edge in all_edges(part)]
        fillet_edges, fillet_signatures = select_exact_edges(part, vertical_corner_predicate(-20, 0, 50, 30), "R5 外立角", 4)
        result["fillet_selection"] = fillet_signatures
        fillet_feature = call(result, "sw_part.fillet", part.FeatureManager.FeatureFillet, 195, mm(5), 0, 0, None, None, None)
        if fillet_feature is not None:
            fillet_feature.Name = "Fillet_R5"
        clear(part)
        part.ForceRebuild3(False)

        # “一侧 2×45°”按一个顶边、2 mm 距离、45°解释；选择仍走子技能的几何谓词。
        chamfer_edges, chamfer_signatures = select_exact_edges(part, _top_side_edge_predicate, "一侧顶边 C2x45", 1)
        result["chamfer_selection"] = chamfer_signatures
        chamfer_feature = call(result, "sw_part.chamfer", chamfer, part, mm(2), 45)
        if chamfer_feature is not None:
            chamfer_feature.Name = "Chamfer_C2x45"
        clear(part)
        part.ForceRebuild3(False)

        if not call(result, "SolidWorksSession.save(SLDPRT)", session.save, part, str(paths["part"])):
            raise RuntimeError("SLDPRT 保存失败")
        result["feature_tree_before_reopen"] = collect_model_summary(part)
        result["geometry_before_reopen"] = collect_geometry_measurements(part)
        expected = [{"id": "center_D20", "diameter_mm": 20, "position_mm": [0, 0, 0]}] + [
            {"id": f"corner_{i+1}_D8", "diameter_mm": 8, "position_mm": [x, y, 0]} for i, (x, y) in enumerate(corners)
        ]
        result["hole_validation"] = validate_hole_positions(result["geometry_before_reopen"], expected)
        review, review_path = run_review(part, OUT / "part_review", basename="plate", expected_outputs=[paths["part"]])
        result["part_review"] = {"path": str(review_path), "evaluation": review.get("evaluation"), "checks": review.get("checks")}

        # 明确测试“读取已有 SLDPRT”与 Feature Tree/B-Rep 读取，而非复用内存对象。
        session.close(title=part_title)
        reopened = call(result, "SolidWorksSession.open(existing SLDPRT)", session.open, str(paths["part"]), read_only=True, silent=True)
        if reopened is None:
            raise RuntimeError("重新打开 SLDPRT 失败")
        part = reopened
        part_title = str(get_com_member(part, "GetTitle"))
        result["feature_tree_after_reopen"] = collect_model_summary(part)
        result["geometry_after_reopen"] = collect_geometry_measurements(part)

        drawing = call(result, "SolidWorksSession.new_drawing", session.new_drawing)
        if drawing is None:
            raise RuntimeError("新建工程图失败")
        drawing_title = str(get_com_member(drawing, "GetTitle"))
        templates = _drawing_templates()
        result["drawing_templates"] = templates
        result["sheet_setup"] = call(result, "sw_drawing.setup_current_sheet_as_a3", setup_current_sheet_as_a3, drawing, templates, require_gbt=True)
        layout = plan_standard_view_layout((mm(100), mm(60), mm(20)), paper_size="A3", projection="first_angle")
        result["view_layout"] = layout
        result["standard_views"] = call(result, "sw_drawing.create_adaptive_standard_views", create_adaptive_standard_views, drawing, str(paths["part"]), layout)
        call(result, "SolidWorksSession.save(SLDDRW first save)", session.save, drawing, str(paths["drawing"]))
        result["center_marks"] = call(result, "sw_drawing.auto_insert_center_marks", auto_insert_center_marks, drawing, [
            {"id": "CM-HOLES", "view": "Front", "count": 5, "targets": ["holes"]}
        ])
        result["model_dimensions"] = call(result, "sw_drawing.insert_dimensions", insert_dimensions, drawing)
        result["dimension_arrangement"] = call(result, "sw_drawing.auto_arrange_drawing_dimensions", auto_arrange_drawing_dimensions, drawing)
        # 此接口要求调用方先创建并选择剖切线；有意记录无高层剖切线创建器时的真实返回。
        result["section_view_without_cutline"] = call(result, "sw_drawing.add_section_view", add_section_view, drawing, 0.2, 0.1)
        result["drawing_structure"] = inspect_drawing_structure(drawing, paper_size_hint="A3", title_block_box=layout.get("title_block_box"))
        call(result, "SolidWorksSession.save(SLDDRW final)", session.save, drawing, str(paths["drawing"]))
        result["pdf_export"] = call(result, "sw_drawing.export_sheet_to_pdf", export_sheet_to_pdf, drawing, str(paths["pdf"]), sw_app=session.sw)
        result["dxf_export"] = call(result, "sw_export.export_to_dxf", export_to_dxf, drawing, str(paths["dxf"]))
        result["dwg_export"] = call(result, "sw_export.export_to_dxf(.dwg)", export_to_dxf, drawing, str(paths["dwg"]))
        result["outputs"] = {key: {"path": str(path), "exists": path.is_file(), "size_bytes": path.stat().st_size if path.is_file() else 0} for key, path in paths.items()}
    except Exception as exc:
        result["fatal_exception"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        for call_record in result["calls"]:
            if call_record["status"] != "pass":
                result["failures"].append(call_record)
        result["finished"] = datetime.now().isoformat(timespec="seconds")
        (OUT / "test_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        if drawing_title:
            session.close(title=drawing_title)
        if part_title:
            session.close(title=part_title)
        session.quit_owned_instance()
    return result


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if "fatal_exception" not in outcome else 1)
