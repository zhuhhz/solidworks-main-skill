from __future__ import annotations

import argparse, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend.solidworks_backend import execute
from inference.feature_hypothesis import infer_feature_graph
from parser.structured_input import load_structured_input
from schemas.modeling_plan import ModelingOperation, ModelingPlan
from validation.projection_consistency import validate as validate_projection
from validation.reconstruction_validator import validate as validate_reconstruction
from validation.roundtrip_validator import validate as validate_roundtrip
from validation.roundtrip_geometry_validator import validate as validate_geometry_roundtrip
from validation.negative_tests import run as run_negative_tests


def build_plan(features):
    base = features.base_block
    ops = [ModelingOperation("base_extrude", "Front Plane", {"type": "rectangle", "width_mm": base.width, "height_mm": base.height}, base.depth)]
    ops += [ModelingOperation("boss_extrude", "Plane_Base_Top", {"type": "rectangle", "width_mm": b.width, "height_mm": b.height, "plane_offset_mm": base.depth}, b.depth) for b in features.bosses]
    hole_plane = "Plane_Boss_Top" if features.bosses else "Front Plane"
    ops += [ModelingOperation("cut_extrude_through_circle", hole_plane, {"type": "circle", "diameter_mm": h.diameter, "center_x_mm": h.center_x, "center_y_mm": h.center_y, "plane_offset_mm": base.depth + sum(b.depth for b in features.bosses)}, direction="through_all") for h in features.holes]
    return ModelingPlan(ops)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--case", default="case_001_block_hole"); args = parser.parse_args()
    case_path = ROOT / "benchmarks" / f"{args.case}.json"; out = ROOT / "results" / args.case
    out.mkdir(parents=True, exist_ok=True)
    graph = load_structured_input(case_path); consistency = validate_projection(graph); features = infer_feature_graph(graph)
    result = {"run_at": datetime.now().isoformat(timespec="seconds"), "case": args.case, "projection_graph": graph.to_dict(), "input_consistency": consistency, "feature_graph": features.to_dict()}
    if args.case == "case_002_step_block": result["negative_tests"] = run_negative_tests(graph)
    if consistency["status"] != "PASS" or features.status != "PASS":
        result.update({"status": "AMBIGUOUS" if features.status == "AMBIGUOUS" else "FAIL", "backend": "not_called"})
    else:
        plan = build_plan(features); result["modeling_plan"] = plan.to_dict(); backend = execute(plan, out, args.case); result["solidworks_backend"] = backend
        result["reconstruction_qa"] = validate_reconstruction(features, backend); level_1 = validate_roundtrip(graph, features, backend)
        try:
            from drawing.drawing_geometry_extractor import extract
            level_2 = validate_geometry_roundtrip(graph, extract(backend["drawing_path"]))
        except Exception as exc:
            level_2 = {"status": "FAIL", "reason": repr(exc)}
        result["roundtrip"] = {"level_1_projection": level_1, "level_2_vector_geometry": level_2}
        result["roundtrip_qa"] = level_1  # retained for Benchmark 001 consumers
        result["status"] = "PASS" if result["reconstruction_qa"]["status"] == "PASS" and level_1["status"] == "PASS" and level_2["status"] == "PASS" else "PARTIAL" if result["reconstruction_qa"]["status"] == "PASS" and level_1["status"] == "PASS" else "FAIL"
    (out / "benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
