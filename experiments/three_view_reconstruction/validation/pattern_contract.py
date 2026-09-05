"""B006 bounded contract gates. No imports from any CAD backend."""
from collections import Counter
import math
from schemas.pattern_feature import PatternOperation


def _fail(code, reason):
    return {"status": "FAIL", "error_code": code, "reason": reason}


def _near(actual, expected):
    return (isinstance(actual, (int, float)) and not isinstance(actual, bool)
            and math.isfinite(actual) and abs(actual - expected) <= 0.01)


def _vector(actual, expected):
    return isinstance(actual, (tuple, list)) and len(actual) == len(expected) and all(
        _near(a, b) for a, b in zip(actual, expected))


def validate_pattern_graph(graph):
    """Validate the fixed B006 geometry, independently of caller declarations."""
    base, seed, pattern, instances = graph.base, graph.seed, graph.pattern, graph.instances
    if seed is None:
        return _fail("MISSING_SEED", "pattern requires a seed")
    nodes = [base, seed, pattern, *instances]
    ids = [node.feature_id for node in nodes]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        return _fail("FEATURE_ID_INVALID", "feature IDs must be nonempty and unique")
    if (base.dependencies or seed.dependencies != [base.feature_id]
            or pattern.dependencies != [seed.feature_id]
            or any(item.dependencies != [pattern.feature_id] for item in instances)):
        return _fail("DEPENDENCY_VIOLATION", "required chain: Base -> Seed -> Pattern -> Instances")
    if (seed.source_feature_id != base.feature_id or pattern.source_feature_id != seed.feature_id
            or any(item.source_feature_id != seed.feature_id for item in instances)
            or any(item.pattern_id != pattern.feature_id for item in [seed, pattern, *instances])):
        return _fail("PROVENANCE_INVALID", "seed and pattern membership references must resolve")
    if (type(pattern.total_count) is not int or pattern.total_count != 4
            or pattern.includes_seed is not True or len(instances) != 4):
        return _fail("INSTANCE_COUNT_MISMATCH", "four total occurrences including the seed are required")
    indices = [item.instance_index for item in instances]
    if any(type(index) is not int for index in indices) or sorted(indices) != [0, 1, 2, 3]:
        return _fail("INSTANCE_INDEX_INVALID", "indices must be unique 0..3")
    if not _vector((base.width, base.height, base.depth), (100, 60, 20)):
        return _fail("BASE_GEOMETRY_MISMATCH", "B006 base is 100x60x20")
    if not _near(seed.diameter_mm, 10) or not _vector(seed.center_mm, (-35, -10, 0)) or seed.axis != "Z" or seed.through is not True:
        return _fail("SEED_GEOMETRY_MISMATCH", "B006 requires the defined diameter, position, axis and through state")
    if not _near(pattern.spacing_mm, 20):
        return _fail("SPACING_MISMATCH", "B006 pitch is 20 mm")
    if not _vector(pattern.direction, (1, 0, 0)):
        return _fail("DIRECTION_MISMATCH", "B006 direction is signed +X")
    for item in instances:
        expected = (-35 + 20 * item.instance_index, -10, 0)
        if not _vector(item.center_mm, expected):
            return _fail("INSTANCE_POSITION_MISMATCH", f"incorrect position for {item.feature_id}")
    canonical = [base.feature_id, seed.feature_id, pattern.feature_id] + [
        item.feature_id for item in sorted(instances, key=lambda row: row.instance_index)]
    return {"status": "PASS", "canonical_order": canonical,
            "classification": "CANONICAL_ORDER" if ids == canonical else "ORDER_VARIANT_EQUIVALENT"}


def build_pattern_operations(graph):
    result = validate_pattern_graph(graph)
    if result["status"] != "PASS":
        raise ValueError(result["error_code"])
    base, seed, pattern = graph.base, graph.seed, graph.pattern
    return [PatternOperation("op_" + base.feature_id, "base_extrude", base.feature_id, ()),
            PatternOperation("op_" + seed.feature_id, "seed_hole_cut", seed.feature_id, ("op_" + base.feature_id,)),
            PatternOperation("op_" + pattern.feature_id, "linear_pattern", pattern.feature_id, ("op_" + seed.feature_id,))]


def validate_pattern_operations(graph, operations):
    result = validate_pattern_graph(graph)
    if result["status"] != "PASS":
        return result
    if operations != build_pattern_operations(graph):
        return _fail("OPERATION_PROVENANCE_INVALID", "requires Base -> seed_hole_cut -> linear_pattern")
    provenance = {op.source_feature_id: op.operation_id for op in operations}
    for instance in graph.instances:
        provenance[instance.feature_id] = provenance[graph.pattern.feature_id]
    return {"status": "PASS", "feature_operations": provenance,
            "instance_seed_operation": provenance[graph.seed.feature_id]}


def validate_pattern_ownership(graph, expected_entities, evidence):
    """expected_entities is an independent entity_id -> instance_id oracle.

    Exact labels are evidence assertions, not API discovery. This pure gate
    checks completeness and provenance; real correspondence is a later phase.
    """
    result = validate_pattern_graph(graph)
    if result["status"] != "PASS":
        return result
    instance_ids = {item.feature_id for item in graph.instances}
    if set(expected_entities.values()) != instance_ids:
        return _fail("OWNERSHIP_COVERAGE_INVALID", "all four instances need independently expected entities")
    counts = Counter(item.entity_id for item in evidence)
    if set(counts) != set(expected_entities) or any(count != 1 for count in counts.values()):
        return _fail("OWNERSHIP_COVERAGE_INVALID", "missing, extra or duplicate entity evidence")
    for row in evidence:
        if row.state not in {"API_EXACT", "INSTANCE_EXACT"}:
            return _fail("OWNERSHIP_UNRESOLVED", "PATTERN_ONLY is diagnostic and cannot pass")
        if (row.pattern_id != graph.pattern.feature_id or row.instance_id != expected_entities[row.entity_id]
                or row.native_owner_feature_id not in {graph.seed.feature_id, graph.pattern.feature_id}):
            return _fail("OWNERSHIP_MISMATCH", "exact evidence must match expected occurrence and native owner")
    return {"status": "PASS", "instance_count": len(instance_ids), "unresolved_count": 0}
