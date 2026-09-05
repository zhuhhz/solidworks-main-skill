"""B006 explicit ProjectionGraph-to-pattern-instance evidence binding."""
from __future__ import annotations

from collections import Counter, defaultdict
import math

from schemas.pattern_evidence import PatternEvidence
from schemas.pattern_feature import PatternFeatureGraph
from schemas.projection_graph import ProjectionGraph
from validation.pattern_contract import validate_pattern_graph


TOLERANCE_MM = 0.01
SEED_SOURCE_EVIDENCE_ID = "seed_geometry_001"


def _near(actual, expected):
    return math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= TOLERANCE_MM


def _registry(graph: ProjectionGraph):
    result, errors = {}, []
    for view_name in ("front", "top", "left"):
        view = getattr(graph, view_name)
        for collection, kind in (("circles", "CIRCLE"), ("hidden_segments", "HIDDEN_LINE")):
            for primitive in getattr(view, collection):
                primitive_id = primitive.primitive_id
                if not primitive_id:
                    continue
                if primitive_id in result:
                    errors.append(f"duplicate primitive_id: {primitive_id}")
                result[primitive_id] = (view_name, kind, primitive)
    return result, errors


def _individual_geometry_errors(row, instance, seed, graph, target):
    view, kind, primitive = target
    x, y, _ = instance.center_mm
    radius = seed.diameter_mm / 2.0
    errors = []
    if view == "front" and kind == "CIRCLE":
        expected = (x + graph.front.horizontal_extent / 2, y + graph.front.vertical_extent / 2)
        if not (_near(primitive.x, expected[0]) and _near(primitive.y, expected[1])
                and _near(primitive.diameter, seed.diameter_mm)):
            errors.append(f"{row.geometry_reference} contradicts {instance.feature_id} front projection")
    elif view == "top" and kind == "HIDDEN_LINE":
        expected_offsets = (x + graph.top.horizontal_extent / 2 - radius,
                            x + graph.top.horizontal_extent / 2 + radius)
        if not (_near(primitive.x1, primitive.x2)
                and any(_near(primitive.x1, offset) for offset in expected_offsets)
                and _near(abs(primitive.y2 - primitive.y1), graph.top.vertical_extent)):
            errors.append(f"{row.geometry_reference} contradicts {instance.feature_id} top projection")
    else:
        errors.append(f"unsupported individual evidence projection: {view}/{kind}")
    return errors


def _shared_geometry_errors(row, instances, seed, graph, target):
    view, kind, primitive = target
    errors = []
    if view != "left" or kind != "HIDDEN_LINE":
        return [f"shared evidence must be left/HIDDEN_LINE: {row.geometry_reference}"]
    projected_y = {round(item.center_mm[1], 6) for item in instances}
    if len(projected_y) != 1:
        return ["left-view overlap claim is invalid because instance Y positions differ"]
    center_y = instances[0].center_mm[1] + graph.left.vertical_extent / 2
    radius = seed.diameter_mm / 2.0
    expected_offsets = (center_y - radius, center_y + radius)
    if not (_near(primitive.y1, primitive.y2)
            and any(_near(primitive.y1, offset) for offset in expected_offsets)
            and _near(abs(primitive.x2 - primitive.x1), graph.left.horizontal_extent)):
        errors.append(f"{row.geometry_reference} contradicts shared left projection")
    return errors


def bind_pattern_evidence(
    projection_graph: ProjectionGraph,
    feature_graph: PatternFeatureGraph,
    evidence: tuple[PatternEvidence, ...] | list[PatternEvidence],
) -> tuple[PatternFeatureGraph, dict]:
    """Validate explicit occurrence attribution and return its instance graph.

    Coordinates reject bad claims but never select an owner. A missing claim is
    UNATTRIBUTED; it is not repaired using proximity, ordering, or an ID suffix.
    """
    contract = validate_pattern_graph(feature_graph)
    report = {
        "status": "PASS", "error_code": None,
        "attribution_method": "EXPLICIT_PATTERN_EVIDENCE_REFERENCE",
        "owner_guessing_used": False, "unattributed_instance_ids": [],
        "contradictions": [], "instance_evidence": {}, "overlapping_evidence": [],
    }
    if contract["status"] != "PASS":
        report.update(status="FAIL", error_code=contract["error_code"],
                      contradictions=[contract["reason"]])
        return feature_graph, report

    registry, errors = _registry(projection_graph)
    instances = {item.feature_id: item for item in feature_graph.instances}
    all_instance_ids = set(instances)
    reference_counts = Counter(row.geometry_reference for row in evidence)
    if any(count != 1 for count in reference_counts.values()):
        errors.append("geometry references must occur exactly once; overlap uses ownership_set")
    individual = defaultdict(list)
    shared = []
    seed_anchor_found = False

    for row in evidence:
        target = registry.get(row.geometry_reference)
        if target is None:
            errors.append(f"missing geometry_reference: {row.geometry_reference}")
            continue
        actual_view, actual_kind, _ = target
        if (row.view, row.geometry_type) != (actual_view, actual_kind):
            errors.append(f"{row.geometry_reference} declares {row.view}/{row.geometry_type}, "
                          f"but resolves to {actual_view}/{actual_kind}")
        if row.pattern_id != feature_graph.pattern.feature_id or row.seed_feature_id != feature_graph.seed.feature_id:
            errors.append(f"invalid pattern/seed provenance: {row.geometry_reference}")
        if SEED_SOURCE_EVIDENCE_ID in row.source_evidence_ids:
            seed_anchor_found = True
        if len(row.ownership_set) > 1:
            if set(row.ownership_set) != all_instance_ids:
                errors.append(f"incomplete overlapping ownership_set: {row.geometry_reference}")
            else:
                errors.extend(_shared_geometry_errors(
                    row, list(instances.values()), feature_graph.seed, projection_graph, target))
                shared.append(row)
            continue
        instance = instances.get(row.instance_id)
        if instance is None:
            errors.append(f"unknown explicit instance owner: {row.instance_id}")
            continue
        if row.instance_index != instance.instance_index or row.ownership_set != (instance.feature_id,):
            errors.append(f"instance identity mismatch: {row.geometry_reference}")
        if (row.position is None or any(not _near(actual, expected)
                                        for actual, expected in zip(row.position, instance.center_mm))):
            errors.append(f"instance position mismatch: {row.geometry_reference}")
        errors.extend(_individual_geometry_errors(
            row, instance, feature_graph.seed, projection_graph, target))
        individual[instance.feature_id].append(row)

    for instance_id in sorted(instances):
        rows = individual[instance_id]
        counts = Counter((row.view, row.geometry_type) for row in rows)
        report["instance_evidence"][instance_id] = {
            "status": "ATTRIBUTED" if counts[("front", "CIRCLE")] == 1
                      and counts[("top", "HIDDEN_LINE")] == 2 else "UNATTRIBUTED",
            "geometry_references": [row.geometry_reference for row in rows],
            "source_evidence_ids": sorted({item for row in rows for item in row.source_evidence_ids}),
        }
        if report["instance_evidence"][instance_id]["status"] != "ATTRIBUTED":
            report["unattributed_instance_ids"].append(instance_id)
    report["overlapping_evidence"] = [
        {"geometry_reference": row.geometry_reference, "ownership_set": list(row.ownership_set)}
        for row in shared
    ]

    if not seed_anchor_found:
        report.update(status="FAIL", error_code="MISSING_SEED_EVIDENCE")
        errors.append(f"missing seed lineage anchor: {SEED_SOURCE_EVIDENCE_ID}")
    if len(shared) != 2:
        errors.append("two shared left-view hidden-line observations are required")
    if errors:
        if report["error_code"] is None:
            report.update(status="FAIL", error_code="EVIDENCE_ATTRIBUTION_INVALID")
        report["contradictions"] = sorted(set(errors))
    elif report["unattributed_instance_ids"]:
        report.update(status="UNATTRIBUTED", error_code="UNATTRIBUTED")
    return feature_graph, report

    if not seed_anchor_found:
        report.update(status="FAIL", error_code="MISSING_SEED_EVIDENCE",
                      contradictions=["seed occurrence lacks explicit seed geometry provenance"])
        return feature_graph, report

    missing = []
    for instance_id, instance in instances.items():
        rows = individual[instance_id]
        counts = Counter((row.view, row.geometry_type) for row in rows)
        if counts[("front", "CIRCLE")] != 1 or counts[("top", "HIDDEN_LINE")] != 2:
            missing.append(instance_id)
        report["instance_evidence"][instance_id] = {
            "instance_index": instance.instance_index,
            "geometry_references": [row.geometry_reference for row in rows],
            "source_evidence_ids": sorted({item for row in rows for item in row.source_evidence_ids}),
        }
    report["overlapping_evidence"] = [
        {"geometry_reference": row.geometry_reference, "ownership_set": list(row.ownership_set)}
        for row in shared
    ]
    if len(shared) != 2:
        missing.extend(sorted(all_instance_ids))
        report["contradictions"].append("two shared left hidden-line supports are required")
    if errors:
        report.update(status="FAIL", error_code="INPUT_INCONSISTENT",
                      contradictions=sorted(set(errors + report["contradictions"])))
    elif missing:
        report.update(status="UNATTRIBUTED", error_code="UNATTRIBUTED",
                      unattributed_instance_ids=sorted(set(missing)))
    return feature_graph, report
