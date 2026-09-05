"""B005 projection-evidence binding and FeatureGraph construction.

Only explicit primitive references establish attribution. Coordinate checks
validate an existing attribution; they never select the closest owner.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace

from inference.slot_inference import analyze_slot_contract
from parser.projection_mapping import front_to_internal
from schemas.feature_graph import BaseBlock, FeatureGraph, FeatureHypothesis, Hole
from schemas.projection_graph import ProjectionGraph
from schemas.view_geometry import ViewGeometry


TOLERANCE_MM = 0.01
FEATURE_IDS = {"base_001", "hole_001", "slot_001"}
ALLOWED_GEOMETRY = {
    "base_001": {"LINE"},
    "hole_001": {"CIRCLE", "HIDDEN_LINE_PAIR", "HIDDEN_LINE"},
    "slot_001": {"LINE", "ARC", "HIDDEN_LINE_PAIR", "HIDDEN_LINE"},
}


def _primitive_registry(graph: ProjectionGraph) -> tuple[dict[str, tuple[str, str, object]], list[str]]:
    registry: dict[str, tuple[str, str, object]] = {}
    errors: list[str] = []
    collections = (
        ("circles", "CIRCLE"),
        ("hidden_line_pairs", "HIDDEN_LINE_PAIR"),
        ("visible_segments", "LINE"),
        ("hidden_segments", "HIDDEN_LINE"),
        ("arcs", "ARC"),
        ("centerlines", "CENTERLINE"),
    )
    for view_name in ("front", "top", "left"):
        view = getattr(graph, view_name)
        for collection_name, geometry_type in collections:
            for primitive in getattr(view, collection_name):
                primitive_id = getattr(primitive, "primitive_id", None)
                if not primitive_id:
                    continue
                if primitive_id in registry:
                    errors.append(f"duplicate primitive_id: {primitive_id}")
                else:
                    registry[primitive_id] = (view_name, geometry_type, primitive)
    return registry, errors


def _feature_rows(graph: ProjectionGraph):
    result = defaultdict(list)
    for row in graph.feature_evidence_records:
        result[row.feature_id].append(row)
    return result


def _structural_errors(graph: ProjectionGraph, registry) -> list[str]:
    rows = graph.feature_evidence_records
    errors: list[str] = []
    counts = Counter(row.evidence_id for row in rows)
    errors.extend(f"duplicate evidence_id: {value}" for value, count in counts.items() if count > 1)
    references: dict[str, str | None] = {}
    for row in rows:
        if row.feature_id not in FEATURE_IDS:
            errors.append(f"unsupported or unattributed feature_id on {row.evidence_id}")
            continue
        target = registry.get(row.geometry_reference)
        if target is None:
            errors.append(f"missing geometry_reference: {row.geometry_reference}")
            continue
        actual_view, actual_type, _ = target
        if (row.view, row.geometry_type) != (actual_view, actual_type):
            errors.append(
                f"{row.evidence_id} declares {row.view}/{row.geometry_type}, "
                f"but {row.geometry_reference} is {actual_view}/{actual_type}"
            )
        if row.geometry_type not in ALLOWED_GEOMETRY[row.feature_id]:
            errors.append(f"{row.feature_id} cannot consume {row.geometry_type}: {row.evidence_id}")
        prior = references.setdefault(row.geometry_reference, row.feature_id)
        if prior != row.feature_id:
            errors.append(f"{row.geometry_reference} is attributed to both {prior} and {row.feature_id}")
    return errors


def _objects(rows, registry, *, view: str | None = None, geometry_type: str | None = None):
    selected = []
    for row in rows:
        target = registry.get(row.geometry_reference)
        if target is None:
            continue
        actual_view, actual_type, primitive = target
        if (view is None or actual_view == view) and (geometry_type is None or actual_type == geometry_type):
            selected.append(primitive)
    return selected


def _required_counts(rows, requirements: dict[tuple[str, str], int]) -> list[str]:
    actual = Counter((row.view, row.geometry_type) for row in rows)
    return [f"missing {view}/{kind} evidence" for (view, kind), count in requirements.items()
            if actual[(view, kind)] < count]


def _line_spans_depth(line, *, view: str, graph: ProjectionGraph) -> bool:
    if view == "top":
        return abs(line.x1 - line.x2) <= TOLERANCE_MM and abs(abs(line.y2 - line.y1) - graph.top.vertical_extent) <= TOLERANCE_MM
    return abs(line.y1 - line.y2) <= TOLERANCE_MM and abs(abs(line.x2 - line.x1) - graph.left.horizontal_extent) <= TOLERANCE_MM


def _validate_base_outline(graph, rows, registry) -> list[str]:
    contradictions = []
    for view_name in ("front", "top", "left"):
        view = getattr(graph, view_name)
        lines = _objects(rows, registry, view=view_name, geometry_type="LINE")
        expected = {
            ((0.0, 0.0), (view.horizontal_extent, 0.0)),
            ((view.horizontal_extent, 0.0), (view.horizontal_extent, view.vertical_extent)),
            ((0.0, view.vertical_extent), (view.horizontal_extent, view.vertical_extent)),
            ((0.0, 0.0), (0.0, view.vertical_extent)),
        }
        actual = {
            tuple(sorted(((line.x1, line.y1), (line.x2, line.y2))))
            for line in lines
        }
        if actual != expected:
            contradictions.append(f"{view_name} base evidence is not the complete outer rectangle")
    return contradictions


def _infer_hole(graph, rows, registry):
    missing = _required_counts(rows, {
        ("front", "CIRCLE"): 1,
        ("top", "HIDDEN_LINE_PAIR"): 1,
        ("top", "HIDDEN_LINE"): 2,
        ("left", "HIDDEN_LINE_PAIR"): 1,
        ("left", "HIDDEN_LINE"): 2,
    })
    if missing:
        return None, missing, []
    circles = _objects(rows, registry, view="front", geometry_type="CIRCLE")
    top_pairs = _objects(rows, registry, view="top", geometry_type="HIDDEN_LINE_PAIR")
    left_pairs = _objects(rows, registry, view="left", geometry_type="HIDDEN_LINE_PAIR")
    top_lines = _objects(rows, registry, view="top", geometry_type="HIDDEN_LINE")
    left_lines = _objects(rows, registry, view="left", geometry_type="HIDDEN_LINE")
    if not (len(circles) == len(top_pairs) == len(left_pairs) == 1):
        return None, [], ["hole evidence must resolve exactly one circle and one pair in each orthogonal view"]
    circle, top_pair, left_pair = circles[0], top_pairs[0], left_pairs[0]
    contradictions = []
    top_center = (top_pair.offset_1 + top_pair.offset_2) / 2
    left_center = (left_pair.offset_1 + left_pair.offset_2) / 2
    if abs(circle.x - top_center) > TOLERANCE_MM:
        contradictions.append("front/top hole X position conflict")
    if abs(circle.y - left_center) > TOLERANCE_MM:
        contradictions.append("front/left hole Y position conflict")
    if abs(circle.diameter - abs(top_pair.offset_2 - top_pair.offset_1)) > TOLERANCE_MM:
        contradictions.append("front/top hole diameter conflict")
    if abs(circle.diameter - abs(left_pair.offset_2 - left_pair.offset_1)) > TOLERANCE_MM:
        contradictions.append("front/left hole diameter conflict")
    if not all(_line_spans_depth(line, view="top", graph=graph) for line in top_lines):
        contradictions.append("top hole evidence does not span full depth")
    if not all(_line_spans_depth(line, view="left", graph=graph) for line in left_lines):
        contradictions.append("left hole evidence does not span full depth")
    top_offsets = sorted(round(line.x1, 6) for line in top_lines)
    left_offsets = sorted(round(line.y1, 6) for line in left_lines)
    if top_offsets != sorted(round(value, 6) for value in (top_pair.offset_1, top_pair.offset_2)):
        contradictions.append("top hole hidden lines do not realize the attributed pair")
    if left_offsets != sorted(round(value, 6) for value in (left_pair.offset_1, left_pair.offset_2)):
        contradictions.append("left hole hidden lines do not realize the attributed pair")
    if contradictions:
        return None, [], contradictions
    x, y = front_to_internal(circle.x, circle.y, graph.front.horizontal_extent, graph.front.vertical_extent)
    return Hole(
        circle.diameter, x, y, "Z", True,
        feature_id="hole_001",
        source_evidence_ids=[row.evidence_id for row in rows],
        dependencies=["base_001"],
    ), [], []


def _infer_slot(graph, rows, registry):
    missing = _required_counts(rows, {
        ("front", "LINE"): 2,
        ("front", "ARC"): 2,
        ("top", "HIDDEN_LINE_PAIR"): 1,
        ("top", "HIDDEN_LINE"): 4,
        ("left", "HIDDEN_LINE_PAIR"): 1,
        ("left", "HIDDEN_LINE"): 2,
    })
    if missing:
        return None, missing, []
    selected = {
        key: _objects(rows, registry, view=view, geometry_type=kind)
        for key, view, kind in (
            ("front_lines", "front", "LINE"), ("front_arcs", "front", "ARC"),
            ("top_pairs", "top", "HIDDEN_LINE_PAIR"), ("top_lines", "top", "HIDDEN_LINE"),
            ("left_pairs", "left", "HIDDEN_LINE_PAIR"), ("left_lines", "left", "HIDDEN_LINE"),
        )
    }
    isolated = ProjectionGraph(
        projection=graph.projection,
        front=ViewGeometry("front", graph.front.horizontal_extent, graph.front.vertical_extent,
                           visible_segments=selected["front_lines"], arcs=selected["front_arcs"]),
        top=ViewGeometry("top", graph.top.horizontal_extent, graph.top.vertical_extent,
                         hidden_line_pairs=selected["top_pairs"], hidden_segments=selected["top_lines"]),
        left=ViewGeometry("left", graph.left.horizontal_extent, graph.left.vertical_extent,
                          hidden_line_pairs=selected["left_pairs"], hidden_segments=selected["left_lines"]),
        coordinate_convention=graph.coordinate_convention,
        feature_evidence={"straight_slot": {"through_state": "THROUGH"}},
    )
    result = analyze_slot_contract(isolated)
    if result["status"] != "PASS":
        reasons = result.get("contradictions", [result.get("reason", "slot evidence is inconsistent")])
        return None, [], reasons
    slot = replace(
        result["slot"], feature_id="slot_001",
        source_evidence_ids=[row.evidence_id for row in rows], dependencies=["base_001"],
    )
    return slot, [], []


def _feature_report(rows, status: str) -> dict:
    return {
        "status": status,
        "evidence_ids": [row.evidence_id for row in rows],
        "primitive_ids": [row.geometry_reference for row in rows],
        "geometry_types": [row.geometry_type for row in rows],
    }


def build_feature_graph_from_evidence(graph: ProjectionGraph) -> tuple[FeatureGraph, dict]:
    """Create B005 FeatureGraph plus machine-readable attribution diagnostics."""
    registry, registry_errors = _primitive_registry(graph)
    rows_by_feature = _feature_rows(graph)
    structural = registry_errors + _structural_errors(graph, registry)
    referenced = {row.geometry_reference for row in graph.feature_evidence_records}
    unattributed_primitives = sorted(set(registry) - referenced)

    base_rows = rows_by_feature.get("base_001", [])
    hole_rows = rows_by_feature.get("hole_001", [])
    slot_rows = rows_by_feature.get("slot_001", [])
    base = BaseBlock(
        graph.front.horizontal_extent, graph.front.vertical_extent, graph.top.vertical_extent,
        feature_id="base_001", source_evidence_ids=[row.evidence_id for row in base_rows], dependencies=[],
    )
    report = {
        "status": "PASS",
        "error_code": None,
        "owner_guessing_used": False,
        "attribution_method": "EXPLICIT_EVIDENCE_REFERENCE",
        "unattributed_primitive_ids": unattributed_primitives,
        "contradictions": [],
        "features": {},
    }
    if structural:
        report.update(status="FAIL", error_code="EVIDENCE_ATTRIBUTION_INVALID", contradictions=sorted(structural))
        graph_result = FeatureGraph(base_block=base, status="FAIL")
        report["features"] = {
            "base_001": _feature_report(base_rows, "INVALID"),
            "hole_001": _feature_report(hole_rows, "INVALID"),
            "slot_001": _feature_report(slot_rows, "INVALID"),
        }
        return graph_result, report

    base_missing = _required_counts(base_rows, {(view, "LINE"): 4 for view in ("front", "top", "left")})
    base_conflicts = [] if base_missing else _validate_base_outline(graph, base_rows, registry)
    hole, hole_missing, hole_conflicts = _infer_hole(graph, hole_rows, registry)
    slot, slot_missing, slot_conflicts = _infer_slot(graph, slot_rows, registry)
    missing = base_missing + hole_missing + slot_missing
    contradictions = base_conflicts + hole_conflicts + slot_conflicts
    if contradictions:
        report.update(status="FAIL", error_code="INPUT_INCONSISTENT", contradictions=sorted(set(contradictions)))
        status = "FAIL"
    elif missing or unattributed_primitives:
        report.update(status="UNATTRIBUTED", error_code="UNATTRIBUTED", contradictions=sorted(set(missing)))
        status = "AMBIGUOUS"
    else:
        status = "PASS"

    report["features"] = {
        "base_001": _feature_report(base_rows, "UNATTRIBUTED" if base_missing else "INVALID" if base_conflicts else "ATTRIBUTED"),
        "hole_001": _feature_report(hole_rows, "UNATTRIBUTED" if hole_missing else "INVALID" if hole_conflicts else "ATTRIBUTED"),
        "slot_001": _feature_report(slot_rows, "UNATTRIBUTED" if slot_missing else "INVALID" if slot_conflicts else "ATTRIBUTED"),
    }
    hypotheses = []
    if hole is not None:
        hypotheses.append(FeatureHypothesis("through_hole", min(row.confidence for row in hole_rows),
                                            [row.evidence_id for row in hole_rows]))
    if slot is not None:
        hypotheses.append(FeatureHypothesis("STRAIGHT_SLOT", min(row.confidence for row in slot_rows),
                                            [row.evidence_id for row in slot_rows]))
    result = FeatureGraph(
        base_block=base,
        holes=[hole] if hole is not None else [],
        slots=[slot] if slot is not None else [],
        hypotheses=hypotheses,
        status=status,
    )
    return result, report
