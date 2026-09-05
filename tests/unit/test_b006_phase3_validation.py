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


def backend(tmp_path, *, domain="PART_FEATURE_PATTERN", seed_state="API_EXACT",
            generated_state="INSTANCE_EXACT"):
    part, drawing = tmp_path / "case.sldprt", tmp_path / "case.slddrw"
    part.write_bytes(b"part"); drawing.write_bytes(b"drawing")
    rows = []
    for index in range(4):
        is_seed = index == 0
        rows.append({
            "entity_id": f"face_{index}", "pattern_id": "pattern_001",
            "feature_id": f"instance_{index + 1:03}", "seed_id": "seed_hole_001",
            "instance_index": index,
            "owner_feature_id": "seed_hole_001" if is_seed else "pattern_001",
            "ownership_level": seed_state if is_seed else generated_state,
            "persistent_reference": f"face_{index}_ref",
        })
    api_count = sum(row["ownership_level"] == "API_EXACT" for row in rows)
    instance_count = sum(row["ownership_level"] == "INSTANCE_EXACT" for row in rows)
    ownership = {"status": "PASS", "ownership_domain": domain,
                 "strict_api_exact_status": "PASS" if api_count == 4 else "FAIL",
                 "api_exact_count": api_count, "instance_exact_count": instance_count,
                 "unresolved_count": sum(row["ownership_level"] == "OWNERSHIP_UNRESOLVED" for row in rows),
                 "rows": rows}
    tree = {"status": "PASS", "features": [
        {"feature_id": "base_001", "type_name_2": "Extrusion"},
        {"feature_id": "seed_hole_001", "type_name_2": "Cut"},
        {"feature_id": "pattern_001", "type_name_2": "LPattern"}]}
    definition = {"status": "PASS"}
    return {"status": "PASS", "ownership_domain": domain,
            "part_path": str(part), "drawing_path": str(drawing),
            "reopened_read_only": True, "initial_feature_tree": tree,
            "reopened_feature_tree": deepcopy(tree), "initial_pattern_definition": definition,
            "reopened_pattern_definition": definition, "initial_ownership": ownership,
            "reopened_ownership": deepcopy(ownership)}


def test_real_gate_accepts_seed_api_and_generated_instance_exact(tmp_path):
    result = validate_real_backend(graph(), backend(tmp_path))
    assert result["status"] == "PASS"
    assert result["strict_api_exact_status"]["reopened"] == "FAIL"


def test_real_gate_accepts_all_api_exact(tmp_path):
    assert validate_real_backend(graph(), backend(tmp_path, generated_state="API_EXACT"))["status"] == "PASS"


def test_real_gate_fails_closed_without_domain(tmp_path):
    data = backend(tmp_path); data.pop("ownership_domain")
    result = validate_real_backend(graph(), data)
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "OWNERSHIP_DOMAIN_REQUIRED"


def test_real_gate_rejects_assembly_domain(tmp_path):
    result = validate_real_backend(graph(), backend(tmp_path, domain="ASSEMBLY_COMPONENT_PATTERN"))
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "OWNERSHIP_DOMAIN_UNSUPPORTED"


def test_real_gate_rejects_seed_instance_exact(tmp_path):
    result = validate_real_backend(graph(), backend(tmp_path, seed_state="INSTANCE_EXACT"))
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "SEED_API_IDENTITY_REQUIRED"


def test_real_gate_rejects_missing_pattern_id(tmp_path):
    data = backend(tmp_path)
    data["initial_ownership"]["rows"][1].pop("pattern_id")
    result = validate_real_backend(graph(), data)
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "PATTERN_REFERENCE_MISSING"


def test_real_gate_rejects_instance_without_seed_lineage(tmp_path):
    data = backend(tmp_path)
    data["reopened_ownership"]["rows"][1].pop("seed_id")
    result = validate_real_backend(graph(), data)
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["reopened"] == "SEED_REFERENCE_MISSING"


def test_real_gate_rejects_pattern_only(tmp_path):
    result = validate_real_backend(graph(), backend(tmp_path, generated_state="PATTERN_ONLY"))
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "INSTANCE_IDENTITY_UNPROVEN"


def test_real_gate_rejects_unresolved_ownership(tmp_path):
    result = validate_real_backend(graph(), backend(tmp_path, generated_state="OWNERSHIP_UNRESOLVED"))
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["initial"] == "OWNERSHIP_UNRESOLVED"


def test_real_gate_rejects_reopen_mapping_mismatch(tmp_path):
    data = backend(tmp_path)
    data["reopened_ownership"]["rows"][1]["entity_id"] = "reopened_face_1"
    data["reopened_ownership"]["rows"][1]["persistent_reference"] = "reopened_face_1_ref"
    result = validate_real_backend(graph(), data)
    assert result["status"] == "FAIL"
    assert result["ownership_error_codes"]["mapping"] == "REOPEN_OWNERSHIP_MISMATCH"


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
