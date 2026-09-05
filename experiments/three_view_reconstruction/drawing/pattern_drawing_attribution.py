"""B006 vector/semantic roundtrip and explicit occurrence attribution."""
from __future__ import annotations

from drawing.view_orientation import CanonicalViewOrientation, canonicalize
from parser.projection_mapping import map_circles_to_frame, map_lines_to_frame
from validation.primitive_matcher import match, match_line_supports


VIEW_ORDER = ("front", "top", "left")
TARGETS = {"front": CanonicalViewOrientation.FRONT, "top": CanonicalViewOrientation.TOP,
           "left": CanonicalViewOrientation.RIGHT}


def _map(view_name, view, projection, geometry, kind):
    frame = canonicalize(TARGETS[view_name].value, projection.upper())
    if kind == "CIRCLE":
        return map_circles_to_frame(view_name, [geometry], view.horizontal_extent,
                                    view.vertical_extent, frame)[0]
    return map_lines_to_frame(view_name, [geometry], view.horizontal_extent,
                              view.vertical_extent, frame)[0]


def _outline(view):
    return [
        {"x1": 0, "y1": 0, "x2": view.horizontal_extent, "y2": 0},
        {"x1": view.horizontal_extent, "y1": 0, "x2": view.horizontal_extent, "y2": view.vertical_extent},
        {"x1": view.horizontal_extent, "y1": view.vertical_extent, "x2": 0, "y2": view.vertical_extent},
        {"x1": 0, "y1": view.vertical_extent, "x2": 0, "y2": 0},
    ]


def validate_roundtrip(data, semantic_evidence: dict) -> dict:
    graph = data.projection_graph
    hlr_views = semantic_evidence.get("hlr", {}).get("post_reopen", [])
    differential = semantic_evidence.get("differential", {})
    diff_views = differential.get("views", [])
    reports = {}
    hidden_reports = {}
    for index, view_name in enumerate(VIEW_ORDER):
        expected_view = getattr(graph, view_name)
        actual = hlr_views[index] if index < len(hlr_views) else {}
        expected_lines = [_map(view_name, expected_view, graph.projection, item, "LINE")
                          for item in _outline(expected_view)]
        expected_circles = [_map(view_name, expected_view, graph.projection,
                                 item.__dict__, "CIRCLE") for item in expected_view.circles]
        reports[view_name] = {
            "visible_lines": match(expected_lines, actual.get("lines", []), "line"),
            "circles": match(expected_circles, actual.get("circles", []), "circle"),
        }
        expected_hidden = [_map(view_name, expected_view, graph.projection,
                                item.__dict__, "LINE") for item in expected_view.hidden_segments]
        actual_hidden = [item["geometry"] for item in (diff_views[index].get("hidden_supports", [])
                         if index < len(diff_views) else [])]
        hidden_reports[view_name] = match_line_supports(expected_hidden, actual_hidden)
    level2a_pass = all(row["visible_lines"]["status"] == "PASS"
                       and row["circles"]["status"] == "PASS" for row in reports.values())
    level2b_pass = (semantic_evidence.get("status") == "PASS"
                    and differential.get("semantic_provenance") == "HLV_MINUS_HLR"
                    and all(row["status"] == "PASS" for row in hidden_reports.values()))
    return {
        "level_2a_vector_geometry": {"status": "PASS" if level2a_pass else "FAIL", "views": reports},
        "level_2b_drawing_semantics": {
            "status": "PASS" if level2b_pass else "FAIL",
            "semantic_provenance": differential.get("semantic_provenance"),
            "hidden_geometry_matches": hidden_reports,
            "unknown_primitive_count": 0 if level2b_pass else None,
        },
    }


def _expected_rows(data):
    graph = data.projection_graph
    registry = {}
    for view_name in VIEW_ORDER:
        view = getattr(graph, view_name)
        for collection, kind, semantic in (("circles", "CIRCLE", "VISIBLE"),
                                           ("hidden_segments", "LINE", "HIDDEN")):
            for primitive in getattr(view, collection):
                if primitive.primitive_id:
                    registry[primitive.primitive_id] = (view_name, kind, semantic, primitive.__dict__)
    rows = []
    for evidence in data.evidence:
        view_name, kind, semantic, geometry = registry[evidence.geometry_reference]
        rows.append({"geometry_reference": evidence.geometry_reference, "semantic_view": view_name,
                     "geometry_type": kind, "semantic": semantic,
                     "geometry": _map(view_name, getattr(graph, view_name), graph.projection, geometry, kind),
                     "ownership_set": list(evidence.ownership_set)})
    return rows


def _geometry_matches(expected, actual):
    if expected["geometry_type"] == "LINE":
        return match_line_supports([expected["geometry"]], [actual])["status"] == "PASS"
    return match([expected["geometry"]], [actual], "circle")["status"] == "PASS"


def run(data, backend: dict, semantic_evidence: dict) -> dict:
    hlr_views = semantic_evidence.get("hlr", {}).get("post_reopen", [])
    diff_views = semantic_evidence.get("differential", {}).get("views", [])
    actual = {name: {"VISIBLE": [], "HIDDEN": []} for name in VIEW_ORDER}
    for index, name in enumerate(VIEW_ORDER):
        if index < len(hlr_views):
            actual[name]["VISIBLE"] += [("LINE", item) for item in hlr_views[index].get("lines", [])]
            actual[name]["VISIBLE"] += [("CIRCLE", item) for item in hlr_views[index].get("circles", [])]
        if index < len(diff_views):
            actual[name]["HIDDEN"] += [("LINE", item["geometry"])
                                        for item in diff_views[index].get("hidden_supports", [])]
    owner_by_instance = {row.get("instance_id"): row.get("ownership")
                         for row in backend.get("reopened_ownership", {}).get("rows", [])
                         if row.get("instance_id")}
    rows = []
    for wanted in _expected_rows(data):
        candidates = [geometry for kind, geometry in actual[wanted["semantic_view"]][wanted["semantic"]]
                      if kind == wanted["geometry_type"] and _geometry_matches(wanted, geometry)]
        strengths = [owner_by_instance.get(owner) for owner in wanted["ownership_set"]]
        if len(candidates) == 1 and strengths and all(value in {"API_EXACT", "INSTANCE_EXACT"} for value in strengths):
            strength = "API_EXACT" if all(value == "API_EXACT" for value in strengths) else "INSTANCE_EXACT"
            rows.append({**wanted, "status": "ATTRIBUTED", "ownership": strength,
                         "source": "PatternEvidence + HLV/HLR geometry + reopened B-Rep occurrence evidence"})
        else:
            rows.append({**wanted, "status": "UNATTRIBUTED", "ownership": "OWNERSHIP_UNRESOLVED",
                         "candidate_count": len(candidates)})
    unknown = 0 if semantic_evidence.get("status") == "PASS" else 1
    unattributed = sum(row["status"] != "ATTRIBUTED" for row in rows)
    api_exact = sum(row["ownership"] == "API_EXACT" for row in rows)
    instance_exact = sum(row["ownership"] == "INSTANCE_EXACT" for row in rows)
    geometry_status = "PASS" if unknown == unattributed == 0 else "FAIL"
    return {
        "status": geometry_status,
        "strict_api_exact_status": "PASS" if geometry_status == "PASS" and instance_exact == 0 else "FAIL",
        "rows": rows, "shared_projection_rows": [row for row in rows if len(row["ownership_set"]) > 1],
        "unknown_count": unknown, "unattributed_count": unattributed,
        "api_exact_count": api_exact, "instance_exact_count": instance_exact,
        "ownership_rule": "explicit PatternEvidence plus exact equality; no nearest-owner selection",
        "name_matching_used": False, "nearest_geometry_used": False, "array_order_used": False,
    }
