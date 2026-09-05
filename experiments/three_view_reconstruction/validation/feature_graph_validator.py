"""Pure engineering-contract validation for multi-feature graphs and plans."""
from __future__ import annotations

from schemas.feature_graph import FeatureGraph
from schemas.modeling_plan import ModelingPlan


_EXPECTED_OPERATION = {
    "BASE_BLOCK": "base_extrude",
    "BOSS": "boss_extrude",
    "THROUGH_HOLE": "cut_extrude_through_circle",
    "STRAIGHT_SLOT": "cut_extrude_through_slot",
}


def _failure(code: str, reasons: list[str]) -> dict:
    return {"status": "FAIL", "error_code": code, "reasons": reasons}


def _topological_order(nodes) -> tuple[list[str], list[str]]:
    ids = [node.feature_id for node in nodes]
    remaining = {node.feature_id: set(node.dependencies) for node in nodes}
    order: list[str] = []
    while remaining:
        ready = [feature_id for feature_id in ids if feature_id in remaining and not remaining[feature_id]]
        if not ready:
            return order, sorted(remaining)
        for feature_id in ready:
            order.append(feature_id)
            remaining.pop(feature_id)
            for dependencies in remaining.values():
                dependencies.discard(feature_id)
    return order, []


def validate_feature_graph(graph: FeatureGraph) -> dict:
    nodes = graph.to_feature_nodes()
    ids = [node.feature_id for node in nodes]
    if any(not value for value in ids):
        return _failure("MISSING_FEATURE_ID", ["every feature requires a stable feature_id"])
    if len(ids) != len(set(ids)):
        return _failure("DUPLICATE_FEATURE_ID", ["feature_id values must be unique"])

    id_set = set(ids)
    missing = sorted({dependency for node in nodes for dependency in node.dependencies if dependency not in id_set})
    if missing:
        return _failure("DEPENDENCY_VIOLATION", [f"missing dependency: {value}" for value in missing])

    base = nodes[0]
    dependency_reasons = []
    if base.feature_type != "BASE_BLOCK" or base.dependencies:
        dependency_reasons.append("base feature must be the dependency root")
    for node in nodes[1:]:
        if node.dependencies != [base.feature_id]:
            dependency_reasons.append(f"{node.feature_id} must depend directly on {base.feature_id}")
    if dependency_reasons:
        return _failure("DEPENDENCY_VIOLATION", dependency_reasons)

    order, cyclic = _topological_order(nodes)
    if cyclic:
        return _failure("DEPENDENCY_CYCLE", [f"cyclic features: {', '.join(cyclic)}"])

    evidence_owners: dict[str, str] = {}
    evidence_reasons = []
    for node in nodes:
        if not node.parameters:
            evidence_reasons.append(f"{node.feature_id} has no parameters")
        if not node.source_evidence_ids:
            evidence_reasons.append(f"{node.feature_id} has no source evidence")
        for evidence_id in node.source_evidence_ids:
            owner = evidence_owners.setdefault(evidence_id, node.feature_id)
            if owner != node.feature_id:
                evidence_reasons.append(f"{evidence_id} is shared by {owner} and {node.feature_id}")
    if evidence_reasons:
        return _failure("EVIDENCE_BINDING_INVALID", evidence_reasons)

    return {"status": "PASS", "topological_order": order,
            "feature_ids": ids, "dependency_edges": [
                {"parent": dependency, "child": node.feature_id}
                for node in nodes for dependency in node.dependencies
            ]}


def validate_modeling_plan(graph: FeatureGraph, plan: ModelingPlan) -> dict:
    graph_result = validate_feature_graph(graph)
    if graph_result["status"] != "PASS":
        return graph_result

    nodes = graph.to_feature_nodes()
    node_by_id = {node.feature_id: node for node in nodes}
    operations = plan.operations
    operation_ids = [operation.operation_id for operation in operations]
    if any(not value for value in operation_ids) or len(operation_ids) != len(set(operation_ids)):
        return _failure("OPERATION_ID_INVALID", ["operation_id values must be present and unique"])
    operation_by_id = {operation.operation_id: operation for operation in operations}
    source_ids = [operation.source_feature_id for operation in operations]
    if len(source_ids) != len(set(source_ids)) or set(source_ids) != set(node_by_id):
        return _failure("OPERATION_PROVENANCE_INVALID", ["each feature requires exactly one source operation"])

    operation_for_feature = {operation.source_feature_id: operation for operation in operations}
    provenance_reasons = []
    for feature_id, node in node_by_id.items():
        operation = operation_for_feature[feature_id]
        expected_type = _EXPECTED_OPERATION.get(node.feature_type)
        if operation.type != expected_type:
            provenance_reasons.append(f"{feature_id} expected {expected_type}, got {operation.type}")
        expected_dependencies = sorted(
            operation_for_feature[dependency].operation_id for dependency in node.dependencies
        )
        if sorted(operation.depends_on_operation_ids) != expected_dependencies:
            provenance_reasons.append(f"{operation.operation_id} dependencies do not match {feature_id}")
    if provenance_reasons:
        return _failure("DEPENDENCY_VIOLATION", provenance_reasons)

    index = {operation.operation_id: position for position, operation in enumerate(operations)}
    order_reasons = []
    for operation in operations:
        for dependency in operation.depends_on_operation_ids:
            if dependency not in operation_by_id or index[dependency] >= index[operation.operation_id]:
                order_reasons.append(f"{operation.operation_id} executes before dependency {dependency}")
    if order_reasons:
        return _failure("DEPENDENCY_VIOLATION", order_reasons)

    actual_feature_order = source_ids
    canonical_feature_order = [node.feature_id for node in nodes]
    classification = "CANONICAL_ORDER" if actual_feature_order == canonical_feature_order else "ORDER_VARIANT_EQUIVALENT"
    return {
        "status": "PASS",
        "classification": classification,
        "feature_order": actual_feature_order,
        "canonical_feature_order": canonical_feature_order,
        "feature_operations": {feature_id: operation_for_feature[feature_id].type for feature_id in canonical_feature_order},
    }
