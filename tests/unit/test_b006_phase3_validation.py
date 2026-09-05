from copy import deepcopy
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from parser.pattern_structured_input import load_pattern_structured_input
from validation.b006_phase3 import run_negative_controls, validate_real_backend


CASE = ROOT / "benchmarks" / "case_006_pattern.json"


def graph():
    return load_pattern_structured_input(CASE).feature_graph


def backend(tmp_path, *, strict="PASS"):
    part, drawing = tmp_path / "case.sldprt", tmp_path / "case.slddrw"
    part.write_bytes(b"part"); drawing.write_bytes(b"drawing")
    ownership = {"status": "PASS", "strict_api_exact_status": strict,
                 "api_exact_count": 4 if strict == "PASS" else 1,
                 "instance_exact_count": 0 if strict == "PASS" else 3, "unresolved_count": 0}
    tree = {"status": "PASS", "features": [
        {"feature_id": "base_001", "type_name_2": "Extrusion"},
        {"feature_id": "seed_hole_001", "type_name_2": "Cut"},
        {"feature_id": "pattern_001", "type_name_2": "LPattern"}]}
    definition = {"status": "PASS"}
    return {"status": "PASS", "part_path": str(part), "drawing_path": str(drawing),
            "reopened_read_only": True, "initial_feature_tree": tree,
            "reopened_feature_tree": deepcopy(tree), "initial_pattern_definition": definition,
            "reopened_pattern_definition": definition, "initial_ownership": ownership,
            "reopened_ownership": deepcopy(ownership)}


def test_real_gate_requires_api_exact_for_every_occurrence(tmp_path):
    assert validate_real_backend(graph(), backend(tmp_path))["status"] == "PASS"
    result = validate_real_backend(graph(), backend(tmp_path, strict="FAIL"))
    assert result["status"] == "FAIL"
    assert result["checks"]["reopened_api_exact"] is False


def test_required_phase3_negative_controls(tmp_path):
    result = run_negative_controls(graph(), backend(tmp_path))
    assert result["status"] == "PASS"
    assert {key: row["actual"] for key, row in result["results"].items()} == {
        "wrong_count": "INSTANCE_COUNT_MISMATCH",
        "wrong_spacing": "SPACING_MISMATCH",
        "wrong_direction": "DIRECTION_MISMATCH",
        "seed_missing": "MISSING_SEED",
        "instance_missing": "INSTANCE_COUNT_MISMATCH",
        "pattern_type_wrong": "PATTERN_TYPE_MISMATCH",
    }
