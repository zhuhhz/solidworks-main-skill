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


def build_plan(features):
    base = features.base_block
    ops = [ModelingOperation("base_extrude", "Front Plane", {"type": "rectangle", "width_mm": base.width, "height_mm": base.height}, base.depth)]
    ops += [ModelingOperation("cut_extrude_through_circle", "Front Plane", {"type": "circle", "diameter_mm": h.diameter, "center_x_mm": h.center_x, "center_y_mm": h.center_y}, direction="through_all") for h in features.holes]
    return ModelingPlan(ops)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--case", default="case_001_block_hole"); args = parser.parse_args()
    case_path = ROOT / "benchmarks" / f"{args.case}.json"; out = ROOT / "results" / args.case
    out.mkdir(parents=True, exist_ok=True)
    graph = load_structured_input(case_path); consistency = validate_projection(graph); features = infer_feature_graph(graph)
    result = {"run_at": datetime.now().isoformat(timespec="seconds"), "case": args.case, "projection_graph": graph.to_dict(), "input_consistency": consistency, "feature_graph": features.to_dict()}
    if consistency["status"] != "PASS" or features.status != "PASS":
        result.update({"status": "AMBIGUOUS" if features.status == "AMBIGUOUS" else "FAIL", "backend": "not_called"})
    else:
        plan = build_plan(features); result["modeling_plan"] = plan.to_dict(); backend = execute(plan, out, args.case); result["solidworks_backend"] = backend
        result["reconstruction_qa"] = validate_reconstruction(features, backend); result["roundtrip_qa"] = validate_roundtrip(graph, features, backend)
        result["status"] = "PASS" if result["reconstruction_qa"]["status"] == "PASS" and result["roundtrip_qa"]["status"] == "PASS" else "FAIL"
    (out / "benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
