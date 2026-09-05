from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from inference.pattern_evidence_binding import bind_pattern_evidence
from parser.pattern_structured_input import load_pattern_structured_input


CASE = ROOT / "benchmarks" / "case_006_pattern.json"


def case():
    return load_pattern_structured_input(CASE)


def bind(data):
    return bind_pattern_evidence(data.projection_graph, data.feature_graph, data.evidence)


def test_four_instance_evidence_is_complete_and_identity_is_independent():
    data = case()
    graph, report = bind(data)
    assert report["status"] == "PASS"
    assert report["owner_guessing_used"] is False
    assert report["attribution_method"] == "EXPLICIT_PATTERN_EVIDENCE_REFERENCE"
    assert [item.feature_id for item in graph.instances] == [
        "instance_001", "instance_002", "instance_003", "instance_004"]
    assert all(item.dependencies == ["pattern_001"] for item in graph.instances)
    assert {key: row["status"] for key, row in report["instance_evidence"].items()} == {
        f"instance_{index:03}": "ATTRIBUTED" for index in range(1, 5)}


def test_instance_position_wrong_fails_without_reassigning_owner():
    data = case()
    rows = list(data.evidence)
    rows[3] = replace(rows[3], position=(-14, -10, 0))
    _, report = bind_pattern_evidence(data.projection_graph, data.feature_graph, rows)
    assert report["status"] == "FAIL"
    assert report["error_code"] == "EVIDENCE_ATTRIBUTION_INVALID"
    assert any("position mismatch" in item for item in report["contradictions"])
    assert report["owner_guessing_used"] is False


def test_missing_instance_evidence_is_unattributed_not_guessed():
    data = case()
    rows = [row for row in data.evidence if row.ownership_set != ("instance_003",)]
    _, report = bind_pattern_evidence(data.projection_graph, data.feature_graph, rows)
    assert report["status"] == "UNATTRIBUTED"
    assert report["error_code"] == "UNATTRIBUTED"
    assert report["unattributed_instance_ids"] == ["instance_003"]
    assert report["owner_guessing_used"] is False


def test_missing_seed_evidence_fails():
    data = case()
    rows = [replace(row, source_evidence_ids=tuple(
        item for item in row.source_evidence_ids if item != "seed_geometry_001"))
        if "seed_geometry_001" in row.source_evidence_ids else row for row in data.evidence]
    _, report = bind_pattern_evidence(data.projection_graph, data.feature_graph, rows)
    assert report["status"] == "FAIL"
    assert report["error_code"] == "MISSING_SEED_EVIDENCE"


def test_pattern_count_wrong_fails_before_attribution():
    data = case()
    graph = deepcopy(data.feature_graph)
    graph.pattern.total_count = 3
    _, report = bind_pattern_evidence(data.projection_graph, graph, data.evidence)
    assert report["status"] == "FAIL"
    assert report["error_code"] == "INSTANCE_COUNT_MISMATCH"


def test_overlapping_ownership_set_is_preserved():
    data = case()
    _, report = bind(data)
    assert report["status"] == "PASS"
    assert len(report["overlapping_evidence"]) == 2
    assert all(row["ownership_set"] == [
        "instance_001", "instance_002", "instance_003", "instance_004"]
        for row in report["overlapping_evidence"])


def test_swapped_instance_claims_fail_geometric_consistency():
    data = case()
    rows = list(data.evidence)
    first = rows[0]
    rows[0] = replace(first, instance_id="instance_002", instance_index=1,
                      position=(-15, -10, 0), ownership_set=("instance_002",))
    _, report = bind_pattern_evidence(data.projection_graph, data.feature_graph, rows)
    assert report["status"] == "FAIL"
    assert any("contradicts instance_002" in item for item in report["contradictions"])


def test_incomplete_overlap_set_is_rejected_instead_of_forcing_one_owner():
    data = case()
    rows = list(data.evidence)
    rows[-1] = replace(rows[-1], ownership_set=("instance_001", "instance_002"))
    _, report = bind_pattern_evidence(data.projection_graph, data.feature_graph, rows)
    assert report["status"] == "FAIL"
    assert any("incomplete overlapping ownership_set" in item for item in report["contradictions"])
