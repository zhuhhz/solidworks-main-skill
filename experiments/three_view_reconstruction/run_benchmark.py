from __future__ import annotations

import argparse, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PROJECT_ROOT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.solidworks_backend import execute
from inference.feature_hypothesis import infer_feature_graph
from parser.structured_input import load_structured_input
from schemas.modeling_plan import ModelingOperation, ModelingPlan
from validation.projection_consistency import validate as validate_projection
from validation.reconstruction_validator import validate as validate_reconstruction
from validation.roundtrip_validator import validate as validate_roundtrip
from validation.roundtrip_geometry_validator import validate as validate_geometry_roundtrip
from validation.roundtrip_levels import split as split_roundtrip_levels
from validation.drawing_qa import acceptance as drawing_acceptance
from validation.negative_tests import run as run_negative_tests
from validation.b005_phase3 import run_negative_controls, validate_real_backend


def build_plan(features):
    base = features.base_block
    operation_id = lambda feature_id: f"op_{feature_id}"
    dependencies = lambda feature: [operation_id(value) for value in feature.dependencies]
    ops = [ModelingOperation(
        "base_extrude", "Front Plane",
        {"type": "rectangle", "width_mm": base.width, "height_mm": base.height}, base.depth,
        operation_id=operation_id(base.feature_id), source_feature_id=base.feature_id,
        depends_on_operation_ids=dependencies(base),
    )]
    ops += [ModelingOperation(
        "boss_extrude", "Plane_Base_Top",
        {"type": "rectangle", "width_mm": b.width, "height_mm": b.height, "plane_offset_mm": base.depth}, b.depth,
        operation_id=operation_id(b.feature_id), source_feature_id=b.feature_id,
        depends_on_operation_ids=dependencies(b),
    ) for b in features.bosses]
    hole_plane = "Plane_Boss_Top" if features.bosses else "Front Plane"
    ops += [ModelingOperation(
        "cut_extrude_through_circle", hole_plane,
        {"type": "circle", "diameter_mm": h.diameter, "center_x_mm": h.center_x,
         "center_y_mm": h.center_y, "plane_offset_mm": base.depth + sum(b.depth for b in features.bosses)},
        direction="through_all", operation_id=operation_id(h.feature_id), source_feature_id=h.feature_id,
        depends_on_operation_ids=dependencies(h),
    ) for h in features.holes]
    ops += [ModelingOperation(
        "cut_extrude_through_slot", "Front Plane",
        {"type": "straight_slot", "overall_length_mm": s.overall_length_mm, "width_mm": s.width_mm,
         "radius_mm": s.radius_mm, "center_x_mm": s.center_x_mm, "center_y_mm": s.center_y_mm,
         "major_axis": s.major_axis},
        direction="through_all", operation_id=operation_id(s.feature_id), source_feature_id=s.feature_id,
        depends_on_operation_ids=dependencies(s),
    ) for s in features.slots]
    return ModelingPlan(ops)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--case", default="case_001_block_hole"); args = parser.parse_args()
    case_path = ROOT / "benchmarks" / f"{args.case}.json"; out = ROOT / "results" / args.case
    out.mkdir(parents=True, exist_ok=True)
    graph = load_structured_input(case_path); consistency = validate_projection(graph); features = infer_feature_graph(graph)
    result = {"run_at": datetime.now().isoformat(timespec="seconds"), "case": args.case, "projection_graph": graph.to_dict(), "reference_integrity": graph.reference_integrity or {"status": "UNASSESSED"}, "input_consistency": consistency, "feature_graph": features.to_dict()}
    if args.case in {"case_002_step_block", "case_003_straight_slot", "case_004_offset_slot"}: result["negative_tests"] = run_negative_tests(graph)
    if consistency["status"] != "PASS" or features.status != "PASS":
        result.update({"status": "AMBIGUOUS" if features.status == "AMBIGUOUS" else "FAIL", "backend": "not_called"})
    else:
        plan = build_plan(features); result["modeling_plan"] = plan.to_dict(); backend = execute(plan, out, args.case); result["solidworks_backend"] = backend
        result["reconstruction_qa"] = validate_reconstruction(features, backend); level_1 = validate_roundtrip(graph, features, backend)
        result["drawing_qa"] = drawing_acceptance(backend.get("drawing_structure", {}))
        try:
            from drawing.drawing_geometry_extractor import extract as extract_projected_geometry
            from drawing.drawing_semantic_extractor import extract as extract_drawing_semantics
            projected = extract_projected_geometry(
                backend["drawing_path"], upstream_path=backend.get("external_backend_path"),
                drawing_structure=backend.get("drawing_structure"),
            )
            from experiments.hlv_hlr_semantics.run_experiment import run_case as run_semantic_experiment
            semantic_evidence = run_semantic_experiment(
                Path(backend["drawing_path"]), args.case,
                PROJECT_ROOT / "experiments" / "hlv_hlr_semantics" / "results" / args.case,
            )
            level_2 = validate_geometry_roundtrip(graph, projected)
            semantic_graph = extract_drawing_semantics(projected, backend.get("drawing_structure"), semantic_evidence)
            levels = split_roundtrip_levels(level_2, semantic_graph, graph)
            if args.case == "case_005_multi_feature":
                from drawing.drawing_feature_attribution import run as run_feature_attribution
                attributed = run_feature_attribution(
                    graph, backend,
                    PROJECT_ROOT / "experiments" / "hlv_hlr_semantics" / "results" / args.case,
                )
                result["attributed_roundtrip"] = attributed
        except Exception as exc:
            level_2 = {"status": "FAIL", "reason": repr(exc)}
            semantic_graph = {"status": "FAIL", "reason": repr(exc)}
            levels = split_roundtrip_levels(level_2, semantic_graph, graph)
        result["roundtrip"] = {"level_1_projection": level_1, **levels, "drawing_primitive_graph": semantic_graph}
        result["roundtrip_qa"] = level_1  # retained for Benchmark 001 consumers
        technical_pass = result["reconstruction_qa"]["status"] == "PASS" and level_1["status"] == "PASS"
        roundtrip_pass = levels["level_2a_vector_geometry"]["status"] == "PASS" and levels["level_2b_drawing_semantics"]["status"] == "PASS"
        if args.case == "case_005_multi_feature":
            real_gate = validate_real_backend(features, plan, backend)
            negatives = run_negative_controls(features, plan, backend)
            attributed_pass = result.get("attributed_roundtrip", {}).get("status") == "PASS"
            result["b005_phase_3"] = {
                "real_backend": real_gate,
                "negative_controls": negatives,
                "level_1": {"status": "PASS" if real_gate["initial_geometry"]["status"] == real_gate["reopened_geometry"]["status"] == level_1["status"] == "PASS" else "FAIL"},
                "level_2a_feature_attributed": {"status": "PASS" if attributed_pass and levels["level_2a_vector_geometry"]["status"] == "PASS" else "FAIL"},
                "level_2b_feature_attributed": {"status": "PASS" if attributed_pass and levels["level_2b_drawing_semantics"]["status"] == "PASS" else "FAIL",
                                                       "unknown_count": result.get("attributed_roundtrip", {}).get("semantic_graph", {}).get("unknown_count"),
                                                       "unattributed_count": result.get("attributed_roundtrip", {}).get("semantic_graph", {}).get("unattributed_count")},
            }
            all_b005 = (real_gate["status"] == negatives["status"] == "PASS"
                        and result["b005_phase_3"]["level_1"]["status"] == "PASS"
                        and result["b005_phase_3"]["level_2a_feature_attributed"]["status"] == "PASS"
                        and result["b005_phase_3"]["level_2b_feature_attributed"]["status"] == "PASS")
            # Phase 3 may establish a candidate only. Release/benchmark PASS is
            # deliberately reserved for the later acceptance phase.
            result["status"] = "PASS_CANDIDATE" if all_b005 else "NOT_VALIDATED"
        else:
            result["status"] = "PASS" if technical_pass and roundtrip_pass else "PARTIAL" if technical_pass else "FAIL"
    (out / "benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if "attributed_roundtrip" in result:
        (out / "attributed_roundtrip.json").write_text(
            json.dumps(result["attributed_roundtrip"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["status"] in {"PASS", "PARTIAL", "PASS_CANDIDATE"} else 1


if __name__ == "__main__": raise SystemExit(main())
