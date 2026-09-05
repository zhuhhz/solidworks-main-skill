"""Execute and persist the bounded B006 real-SolidWorks validation."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from backend.solidworks_pattern_backend import execute_pattern
from drawing.pattern_drawing_attribution import run as run_pattern_drawing_attribution, validate_roundtrip
from inference.pattern_evidence_binding import bind_pattern_evidence
from parser.pattern_structured_input import load_pattern_structured_input
from validation.b006_phase3 import run_negative_controls, validate_level_1, validate_real_backend
from validation.projection_consistency import validate as validate_projection


def main() -> int:
    name = "case_006_pattern"
    output = ROOT / "results" / name
    output.mkdir(parents=True, exist_ok=True)
    data = load_pattern_structured_input(ROOT / "benchmarks" / f"{name}.json")
    feature_graph, binding = bind_pattern_evidence(
        data.projection_graph, data.feature_graph, data.evidence)
    result = {
        "run_at": datetime.now().isoformat(timespec="seconds"), "case": name,
        "status": "NOT_VALIDATED", "phase": "B006_PHASE_3",
        "projection_graph": data.projection_graph.to_dict(),
        "feature_graph": feature_graph.to_dict(), "evidence_binding": binding,
        "input_consistency": validate_projection(data.projection_graph),
    }
    backend = execute_pattern(feature_graph, output, name)
    result["solidworks_backend"] = backend
    (output / "native_backend_evidence.json").write_text(
        json.dumps(backend, ensure_ascii=False, indent=2), encoding="utf-8")
    result["backend_gate"] = validate_real_backend(feature_graph, backend)
    result["level_1"] = validate_level_1(feature_graph, backend)
    result["negative_tests"] = run_negative_controls(feature_graph, backend)
    semantic_dir = PROJECT_ROOT / "experiments" / "hlv_hlr_semantics" / "results" / name
    try:
        from experiments.hlv_hlr_semantics.run_experiment import run_case
        semantic_evidence = run_case(Path(backend["drawing_path"]), name, semantic_dir)
        levels = validate_roundtrip(data, semantic_evidence)
        attributed = run_pattern_drawing_attribution(data, backend, semantic_evidence)
        result["semantic_evidence"] = semantic_evidence
        result["roundtrip"] = levels
        result["pattern_attributed_roundtrip"] = attributed
    except Exception as exc:
        result["roundtrip"] = {
            "level_2a_vector_geometry": {"status": "FAIL", "reason": repr(exc)},
            "level_2b_drawing_semantics": {"status": "FAIL", "reason": repr(exc)},
        }
        result["pattern_attributed_roundtrip"] = {
            "status": "FAIL", "strict_api_exact_status": "FAIL",
            "unknown_count": None, "unattributed_count": None, "error": repr(exc)}

    level2a = result["roundtrip"]["level_2a_vector_geometry"].get("status")
    level2b = result["roundtrip"]["level_2b_drawing_semantics"].get("status")
    attribution = result["pattern_attributed_roundtrip"]
    all_geometry = (backend.get("status") == "PASS" and result["level_1"]["status"] == "PASS"
                    and level2a == level2b == "PASS" and attribution.get("status") == "PASS")
    all_strict = all_geometry and result["backend_gate"]["status"] == "PASS" \
                 and attribution.get("strict_api_exact_status") == "PASS"
    # The requested hard rule reserves validation for API_EXACT ownership of
    # every occurrence. INSTANCE_EXACT is useful evidence but cannot promote.
    result["status"] = "PASS_CANDIDATE" if all_strict else "NOT_VALIDATED"
    result["decision"] = {
        "geometry_chain_complete": all_geometry,
        "all_occurrences_api_exact": all_strict,
        "rule": "any non-API_EXACT occurrence keeps B006 NOT_VALIDATED",
    }
    (output / "benchmark_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "pattern_attributed_roundtrip.json").write_text(
        json.dumps(result["pattern_attributed_roundtrip"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "backend": backend.get("status"),
        "backend_gate": result["backend_gate"]["status"], "level_1": result["level_1"]["status"],
        "level_2a": level2a, "level_2b": level2b,
        "drawing_attribution": attribution.get("status"),
        "drawing_strict_api_exact": attribution.get("strict_api_exact_status"),
        "unknown": attribution.get("unknown_count"),
        "unattributed": attribution.get("unattributed_count"),
        "part": backend.get("part_path"), "drawing": backend.get("drawing_path"),
    }, ensure_ascii=False, indent=2))
    return 0 if backend.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
