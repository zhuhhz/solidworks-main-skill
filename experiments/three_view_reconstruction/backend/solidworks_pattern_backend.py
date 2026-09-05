"""Main-project B006 adapter over the external SolidWorks execution backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path


configured = os.environ.get("SOLIDWORKS_AUTOMATION_BACKEND_PATH")
UPSTREAM_ROOT = Path(configured) if configured else Path(__file__).resolve().parents[4] / "solidworks-automation-skill"
if not (UPSTREAM_ROOT / "scripts" / "sw_session.py").is_file():
    raise RuntimeError("UPSTREAM_GAP: external solidworks-automation-skill checkout is unavailable")
sys.path.insert(0, str(UPSTREAM_ROOT / "scripts"))

from sw_connect import get_com_member, mm
from sw_drawing import create_standard_views_with_projection, inspect_drawing_structure
from sw_hole_features import create_through_hole
from sw_part import extrude_boss, sketch, sketch_rectangle
from sw_review import collect_geometry_measurements, collect_model_summary, run_review
from sw_session import SolidWorksSession

from backend.ownership_probe import collect_feature_references
from backend.pattern_ownership_probe import (
    collect_pattern_definition, collect_pattern_feature_tree, collect_pattern_ownership,
)


SW_FM_LINEAR_PATTERN = 6  # verified from SW2024 SolidWorks.Interop.swconst.dll


def _last_feature(model):
    feature, last = get_com_member(model, "FirstFeature"), None
    while feature is not None:
        last = feature
        feature = get_com_member(feature, "GetNextFeature")
    return last


def _x_direction_edge(model):
    candidates = []
    for body in get_com_member(model, "GetBodies2", 0, False) or []:
        for edge in get_com_member(body, "GetEdges") or []:
            try:
                curve = get_com_member(edge, "GetCurve")
                if curve is None or not bool(get_com_member(curve, "IsLine")):
                    continue
                values = list(get_com_member(curve, "LineParams") or [])
                if len(values) >= 6 and abs(abs(float(values[3])) - 1.0) <= 1e-6:
                    candidates.append((edge, float(values[3]), values))
            except Exception:
                continue
    if not candidates:
        raise RuntimeError("UPSTREAM_GAP: no exact X-direction edge available for native linear pattern")
    # Any exact X-parallel edge defines the same axis. Selection is based on
    # analytic direction, not a screen coordinate or localized edge name.
    return candidates[0]


def _create_native_linear_pattern(model, seed_feature, spacing_mm: float, count: int):
    model.ClearSelection2(True)
    if not bool(seed_feature.Select2(False, 4)):
        raise RuntimeError("native seed feature Select2(mark=4) failed")
    edge, edge_dx, line_params = _x_direction_edge(model)
    select_data = model.SelectionManager.CreateSelectData
    select_data.Mark = 1
    if not bool(edge.Select4(True, select_data)):
        raise RuntimeError("native X direction edge Select4(mark=1) failed")
    data = model.FeatureManager.CreateDefinition(SW_FM_LINEAR_PATTERN)
    if data is None:
        raise RuntimeError("CreateDefinition(swFmLPattern) returned None")
    data.D1EndCondition = 0
    data.D1ReverseDirection = edge_dx < 0
    data.D1Spacing = mm(spacing_mm)
    data.D1TotalInstances = count
    data.D2EndCondition = 0
    data.D2TotalInstances = 1
    data.D2Spacing = mm(spacing_mm)
    data.GeometryPattern = False
    data.VarySketch = False
    feature = model.FeatureManager.CreateFeature(data)
    model.ClearSelection2(True)
    if feature is None:
        raise RuntimeError("CreateFeature(ILinearPatternFeatureData) returned None")
    return feature, {"api": "CreateDefinition(swFmLPattern=6)->CreateFeature",
                     "selected_direction_line_params": [float(value) for value in line_params],
                     "spacing_mm": spacing_mm, "count": count, "signed_direction": "+X"}


def _close_known_active(session, paths):
    wanted = {str(path.resolve()).casefold() for path in paths}
    try:
        active = session.sw.ActiveDoc
        if active is not None and str(get_com_member(active, "GetPathName")).casefold() in wanted:
            session.sw.CloseDoc(str(get_com_member(active, "GetTitle")))
    except Exception:
        pass


def execute_pattern(graph, output_dir: Path, name: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path = output_dir / f"{name}.sldprt"
    drawing_path = output_dir / f"{name}.slddrw"
    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    part_title = drawing_title = None
    result = {"status": "FAIL", "external_backend_path": str(UPSTREAM_ROOT), "operations": []}
    try:
        _close_known_active(session, (part_path, drawing_path))
        part = session.new_part()
        part_title = str(get_com_member(part, "GetTitle"))
        with sketch(part, "Front Plane") as sketch_name:
            sketch_rectangle(part, 0, 0, mm(graph.base.width), mm(graph.base.height))
        base = extrude_boss(part, sketch_name, mm(graph.base.depth))
        if base is None:
            raise RuntimeError("external backend base extrusion returned None")
        base.Name = "BaseBlock"
        result["operations"].append({"operation_id": "op_base_001", "source_feature_id": "base_001",
                                     "operation": "base_extrude", "api_success": True})

        seed_evidence = create_through_hole(
            part, (mm(graph.seed.center_mm[0]), mm(graph.seed.center_mm[1])),
            mm(graph.seed.diameter_mm), plane_name="Front Plane", name="SeedHole_D10")
        seed = _last_feature(part)
        if seed is None:
            raise RuntimeError("external backend through-hole feature provenance unavailable")
        result["operations"].append({"operation_id": "op_seed_hole_001",
                                     "source_feature_id": "seed_hole_001", "operation": "seed_hole_cut",
                                     "api_success": True, "evidence": seed_evidence})

        pattern, pattern_api = _create_native_linear_pattern(
            part, seed, graph.pattern.spacing_mm, graph.pattern.total_count)
        pattern.Name = "LinearPattern_4x_D10"
        result["operations"].append({"operation_id": "op_pattern_001", "source_feature_id": "pattern_001",
                                     "operation": "linear_pattern", "api_success": True,
                                     "evidence": pattern_api})
        part.ForceRebuild3(False)
        if not session.save(part, str(part_path)):
            raise RuntimeError("SLDPRT save failed")
        refs = collect_feature_references(part, {"base_001": base, "seed_hole_001": seed, "pattern_001": pattern})
        result["feature_identity"] = {"references": refs,
                                      "source": "IModelDocExtension.GetPersistReference3",
                                      "feature_names_excluded_from_identity": True}
        definition = collect_pattern_definition(part, refs["pattern_001"])
        result["initial_pattern_definition"] = definition
        result["initial_feature_tree"] = collect_pattern_feature_tree(part, refs, definition)
        result["initial_ownership"] = collect_pattern_ownership(part, refs, graph, definition)
        result["initial_geometry"] = collect_geometry_measurements(part)
        result["model_summary"] = collect_model_summary(part)
        review, review_path = run_review(part, output_dir / "review", basename=name, expected_outputs=[part_path])
        result["review"] = {"path": str(review_path), "evaluation": review["evaluation"]}

        session.close(title=part_title)
        part = session.open(str(part_path), read_only=True, silent=True)
        part_title = str(get_com_member(part, "GetTitle"))
        result["reopened_read_only"] = True
        result["reopened_model_summary"] = collect_model_summary(part)
        definition = collect_pattern_definition(part, refs["pattern_001"])
        result["reopened_pattern_definition"] = definition
        result["reopened_feature_tree"] = collect_pattern_feature_tree(part, refs, definition)
        result["reopened_ownership"] = collect_pattern_ownership(part, refs, graph, definition)
        result["reopened_geometry"] = collect_geometry_measurements(part)

        drawing = session.new_drawing()
        drawing_title = str(get_com_member(drawing, "GetTitle"))
        result["drawing_create"] = create_standard_views_with_projection(
            drawing, str(part_path), projection="third_angle")
        if not session.save(drawing, str(drawing_path)):
            raise RuntimeError("SLDDRW save failed")
        result["drawing_structure"] = inspect_drawing_structure(drawing)
        result.update(status="PASS", part_path=str(part_path), drawing_path=str(drawing_path))
    except Exception as exc:
        result.update(status="FAIL", error=repr(exc))
    finally:
        if drawing_title:
            session.close(title=drawing_title)
        if part_title:
            session.close(title=part_title)
        session.quit_owned_instance()
    return result
