from pathlib import Path
import sys
from dataclasses import replace
import pytest

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))
from schemas.feature_graph import BaseBlock
from schemas.pattern_feature import SeedFeature, PatternFeature, InstanceFeature, PatternFeatureGraph, PatternOwnership
from validation.pattern_contract import (validate_pattern_graph, build_pattern_operations,
                                         validate_pattern_operations, validate_pattern_ownership)


def graph():
    return PatternFeatureGraph(
        BaseBlock(100, 60, 20),
        SeedFeature("seed_hole_001", "pattern_001", "base_001", (-35, -10, 0), 10, ["base_001"]),
        PatternFeature("pattern_001", "pattern_001", "seed_hole_001", 20, (1, 0, 0), 4, ["seed_hole_001"]),
        [InstanceFeature(f"instance_{i+1:03}", "pattern_001", "seed_hole_001", i,
                         (x, -10, 0), ["pattern_001"]) for i, x in enumerate((-35, -15, 5, 25))])


def test_four_instances_and_role_serialization():
    g = graph()
    assert validate_pattern_graph(g)["status"] == "PASS"
    data = g.to_dict()
    assert data["seed"]["feature_role"] == "SEED"
    assert data["pattern"]["feature_role"] == "PATTERN"
    assert {item["feature_role"] for item in data["instances"]} == {"INSTANCE"}


@pytest.mark.parametrize("count", [3, 5, True])
def test_wrong_count_fails(count):
    g = graph(); g.pattern.total_count = count
    assert validate_pattern_graph(g)["status"] == "FAIL"


def test_missing_instance_fails():
    g = graph(); g.instances.pop()
    assert validate_pattern_graph(g)["error_code"] == "INSTANCE_COUNT_MISMATCH"


def test_wrong_spacing_even_with_consistent_positions_fails():
    g = graph(); g.pattern.spacing_mm = 18
    for item in g.instances:
        item.center_mm = (-35 + 18 * item.instance_index, -10, 0)
    assert validate_pattern_graph(g)["error_code"] == "SPACING_MISMATCH"


@pytest.mark.parametrize("direction", [(-1, 0, 0), (0, 1, 0), (float("nan"), 0, 0)])
def test_wrong_direction_fails(direction):
    g = graph(); g.pattern.direction = direction
    assert validate_pattern_graph(g)["error_code"] == "DIRECTION_MISMATCH"


def test_missing_seed_fails():
    g = graph(); g.seed = None
    assert validate_pattern_graph(g)["error_code"] == "MISSING_SEED"


def test_instance_direct_base_dependency_fails():
    g = graph(); g.instances[1].dependencies = ["base_001"]
    assert validate_pattern_graph(g)["error_code"] == "DEPENDENCY_VIOLATION"


def test_pattern_instance_enumeration_order_variant():
    g = graph(); g.instances.reverse()
    assert validate_pattern_graph(g)["classification"] == "ORDER_VARIANT_EQUIVALENT"
    assert [op.operation_type for op in build_pattern_operations(g)] == ["base_extrude", "seed_hole_cut", "linear_pattern"]


def test_execution_order_cannot_reverse_dependencies():
    g = graph(); ops = build_pattern_operations(g)
    assert validate_pattern_operations(g, list(reversed(ops)))["status"] == "FAIL"


def test_operation_provenance_for_all_instances():
    g = graph(); result = validate_pattern_operations(g, build_pattern_operations(g))
    assert result["status"] == "PASS"
    assert all(result["feature_operations"][item.feature_id] == "op_pattern_001" for item in g.instances)


@pytest.mark.parametrize("mutation", ["index", "position", "seed", "source"])
def test_identity_and_geometry_mutations_fail(mutation):
    g = graph()
    if mutation == "index": g.instances[1].instance_index = 0
    if mutation == "position": g.instances[1].center_mm = (5, -10, 0)
    if mutation == "seed": g.seed.diameter_mm = 12
    if mutation == "source": g.pattern.source_feature_id = "absent"
    assert validate_pattern_graph(g)["status"] == "FAIL"


def ownership(g, state="INSTANCE_EXACT"):
    expected = {f"face_{i}": item.feature_id for i, item in enumerate(g.instances)}
    rows = [PatternOwnership(entity, "pattern_001", owner, "pattern_001", state,
                             "synthetic unit fixture, not CAD evidence", entity + "_ref")
            for entity, owner in expected.items()]
    return expected, rows


@pytest.mark.parametrize("state", ["API_EXACT", "INSTANCE_EXACT"])
def test_exact_ownership_states(state):
    g = graph(); expected, rows = ownership(g, state)
    assert validate_pattern_ownership(g, expected, rows)["status"] == "PASS"


@pytest.mark.parametrize("state", ["PATTERN_ONLY", "OWNERSHIP_UNRESOLVED"])
def test_diagnostic_states_cannot_pass(state):
    g = graph(); expected, rows = ownership(g)
    rows[0] = replace(rows[0], instance_id=None, state=state)
    assert validate_pattern_ownership(g, expected, rows)["status"] == "FAIL"


def test_ownership_swap_and_missing_rows_fail():
    g = graph(); expected, rows = ownership(g)
    assert validate_pattern_ownership(g, expected, rows[:-1])["status"] == "FAIL"
    rows[0] = replace(rows[0], instance_id="instance_002")
    assert validate_pattern_ownership(g, expected, rows)["status"] == "FAIL"


def test_exact_label_without_identity_evidence_rejected():
    with pytest.raises(ValueError):
        PatternOwnership("face", "pattern_001", "instance_001", "seed_hole_001", "API_EXACT", "fixture")
