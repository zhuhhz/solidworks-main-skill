"""API-exact projected-primitive attribution for B005.

The drawing-context persistent reference identifies the component context and
is not sufficient by itself to distinguish features.  We therefore resolve
each model feature from its persistent reference, obtain its view-context
counterpart with IView.GetCorresponding, and compare that COM identity with
IFace2.GetFeature reached from GetPolylines7 entities.  No names or geometric
proximity participate in owner selection.
"""
from __future__ import annotations

import base64
from pathlib import Path
import sys

from win32com.client import gencache

from drawing.drawing_geometry_extractor import DRAWING_DOC_CLSID, _line_or_circle, _records
from drawing.view_coordinate_transform import normalize_geometry
from drawing.view_orientation import CanonicalViewOrientation, canonicalize
from parser.projection_mapping import map_arcs_to_frame, map_circles_to_frame, map_lines_to_frame
from validation.feature_attribution import validate_feature_attribution
from validation.primitive_matcher import match, match_line_supports


def select_topological_owner(candidate_feature_ids: list[str | None]) -> str | None:
    """Select an operation owner from exact adjacent-face owners."""
    candidates = {value for value in candidate_feature_ids if value}
    descendants = candidates - {"base_001"}
    if len(descendants) == 1:
        return next(iter(descendants))
    if not descendants and candidates == {"base_001"}:
        return "base_001"
    return None


def _same_com(left, right) -> bool:
    try:
        return bool(left._oleobj_ == right._oleobj_)
    except Exception:
        return False


def _faces(entity) -> list:
    try:
        return [face for face in entity.GetTwoAdjacentFaces2 if face is not None]
    except Exception:
        try:
            face = entity.GetFace
            return [face] if face is not None else []
        except Exception:
            return []


def _context_features(view, feature_references: dict[str, str]):
    model = view.ReferencedDocument
    extension = model.Extension
    result = {}
    errors = {}
    for feature_id, encoded in feature_references.items():
        try:
            feature, error_code = extension.GetObjectByPersistReference3(base64.b64decode(encoded))
            corresponding = view.GetCorresponding(feature) if feature is not None and error_code == 0 else None
            if corresponding is None:
                errors[feature_id] = f"GetCorresponding unavailable (resolve error={error_code})"
            else:
                result[feature_id] = corresponding
        except Exception as exc:
            errors[feature_id] = repr(exc)
    return result, errors


def _entity_owner(entity, contextual_features: dict[str, object]) -> tuple[str | None, list[str]]:
    candidates = []
    for face in _faces(entity):
        try:
            owner = face.GetFeature
        except Exception:
            continue
        candidates.extend(feature_id for feature_id, feature in contextual_features.items()
                          if _same_com(owner, feature))
    candidates = sorted(set(candidates))
    return select_topological_owner(candidates), candidates


def _capture_file(path: Path, upstream_path: Path, feature_references: dict[str, str],
                  declared_views: list[dict]) -> dict:
    sys.path.insert(0, str(upstream_path / "scripts"))
    from sw_session import SolidWorksSession

    session = SolidWorksSession(version=2024, visible=True, wait_seconds=20)
    model = session.open(str(path), read_only=True, silent=True)
    try:
        module = gencache.GetModuleForCLSID(DRAWING_DOC_CLSID)
        drawing = module.IDrawingDoc(model._oleobj_)
        raw_view = module.IView(drawing.GetFirstView()._oleobj_).GetNextView()
        views = []
        while raw_view is not None:
            view = module.IView(raw_view._oleobj_)
            ratio = list(view.ScaleRatio)
            scale = float(ratio[0]) / float(ratio[1])
            raw = list(view.GetPolyLinesAndCurves(0))  # primes GetPolylines7 on SW2024
            records = list(_records(raw))
            entities, _polylines = view.GetPolylines7(1)
            contextual, context_errors = _context_features(view, feature_references)
            rows = []
            for index, ((kind, geometry, _attributes, points), entity) in enumerate(zip(records, entities)):
                geometry_type, payload = _line_or_circle(kind, points, scale, geometry)
                feature_id, candidates = _entity_owner(entity, contextual)
                rows.append({
                    "primitive_id": f"view{len(views)}:polyline:{index}",
                    "geometry_type": geometry_type.upper(),
                    "geometry": payload,
                    "actual_feature_id": feature_id,
                    "candidate_feature_ids": candidates,
                    "ownership": "API_EXACT" if feature_id else "OWNERSHIP_UNRESOLVED",
                    "source": "IView.GetPolylines7->IEdge/ISilhouetteEdge->IFace2.GetFeature+IView.GetCorresponding",
                })
            # Normalize by type without losing entity-to-geometry row identity.
            lines = [row["geometry"] for row in rows if row["geometry_type"] == "LINE"]
            circles = [row["geometry"] for row in rows if row["geometry_type"] == "CIRCLE"]
            arcs = [row["geometry"] for row in rows if row["geometry_type"] == "ARC"]
            lines, circles, arcs, origin = normalize_geometry(lines, circles, arcs)
            normalized = {"LINE": iter(lines), "CIRCLE": iter(circles), "ARC": iter(arcs)}
            for row in rows:
                if row["geometry_type"] in normalized:
                    row["geometry"] = next(normalized[row["geometry_type"]])
            declared = declared_views[len(views)] if len(views) < len(declared_views) else {}
            # The third-angle drawing backend creates a physical RIGHT view to
            # represent the input schema's left-view Z/Y frame.  Keep this
            # mapping explicit; do not infer it from localized view names.
            semantic_view = {"right": "left"}.get(declared.get("semantic_view"),
                                                   declared.get("semantic_view"))
            views.append({
                "index": len(views), "name": str(view.Name),
                "semantic_view": semantic_view, "rows": rows,
                "context_resolution_errors": context_errors,
                "normalization_origin_mm": list(origin),
            })
            raw_view = view.GetNextView()
        return {"status": "PASS", "path": str(path), "views": views}
    finally:
        session.close(model=model)
        session.quit_owned_instance()


def _is_present(row: dict, visible_rows: list[dict]) -> bool:
    kind = row["geometry_type"]
    candidates = [item["geometry"] for item in visible_rows if item["geometry_type"] == kind]
    if kind == "LINE":
        return match_line_supports([row["geometry"]], candidates)["status"] == "PASS"
    if kind in {"CIRCLE", "ARC"}:
        return match([row["geometry"]], candidates, kind.lower())["status"] == "PASS"
    return False


def combine_semantics(hlr: dict, hlv: dict) -> dict:
    views = []
    for removed, visible in zip(hlr.get("views", []), hlv.get("views", [])):
        visible_rows = [dict(row, semantic="VISIBLE", semantic_source="HLR_CAPTURE")
                        for row in removed["rows"]]
        hidden_rows = [dict(row, semantic="HIDDEN", semantic_source="HLV_MINUS_HLR")
                       for row in visible["rows"] if not _is_present(row, removed["rows"])]
        rows = visible_rows + hidden_rows
        views.append({"index": removed["index"], "semantic_view": removed.get("semantic_view"),
                      "rows": rows})
    all_rows = [row for view in views for row in view["rows"]]
    unknown = sum(row.get("semantic") not in {"VISIBLE", "HIDDEN"} for row in all_rows)
    unattributed = sum(not row.get("actual_feature_id") for row in all_rows)
    return {"status": "PASS" if unknown == unattributed == 0 else "FAIL", "views": views,
            "unknown_count": unknown, "unattributed_count": unattributed,
            "ownership_required": "API_EXACT"}


def _expected_rows(graph) -> list[dict]:
    registry = {}
    for view_name in ("front", "top", "left"):
        view = getattr(graph, view_name)
        for collection, kind in (("visible_segments", "LINE"), ("hidden_segments", "LINE"),
                                 ("circles", "CIRCLE"), ("arcs", "ARC")):
            for primitive in getattr(view, collection):
                if primitive.primitive_id:
                    registry[primitive.primitive_id] = (view_name, kind, primitive.__dict__,
                                                        "HIDDEN" if collection == "hidden_segments" else "VISIBLE")
    targets = {"front": CanonicalViewOrientation.FRONT, "top": CanonicalViewOrientation.TOP,
               "left": CanonicalViewOrientation.RIGHT}
    output = []
    for evidence in graph.feature_evidence_records:
        item = registry.get(evidence.geometry_reference)
        if item is None:
            continue
        view_name, kind, geometry, semantic = item
        view = getattr(graph, view_name)
        frame = canonicalize(targets[view_name].value, graph.projection.upper())
        if kind == "LINE":
            transformed = map_lines_to_frame(view_name, [geometry], view.horizontal_extent, view.vertical_extent, frame)[0]
        elif kind == "CIRCLE":
            transformed = map_circles_to_frame(view_name, [geometry], view.horizontal_extent, view.vertical_extent, frame)[0]
        else:
            transformed = map_arcs_to_frame(view_name, [geometry], view.horizontal_extent, view.vertical_extent, frame)[0]
        output.append({"primitive_id": evidence.geometry_reference, "expected_feature_id": evidence.feature_id,
                       "semantic_view": view_name, "geometry_type": kind, "semantic": semantic,
                       "geometry": transformed})
    return output


def validate_attributed_roundtrip(graph, semantic: dict) -> dict:
    expected = _expected_rows(graph)
    actual_views = {view.get("semantic_view"): view for view in semantic.get("views", [])}
    matches = []
    partitions = []
    for feature_id in ("base_001", "hole_001", "slot_001"):
        for view_name in ("front", "top", "left"):
            for kind in ("LINE", "CIRCLE", "ARC"):
                for semantic_kind in ("VISIBLE", "HIDDEN"):
                    wanted = [row for row in expected if row["expected_feature_id"] == feature_id
                              and row["semantic_view"] == view_name and row["geometry_type"] == kind
                              and row["semantic"] == semantic_kind]
                    if not wanted:
                        continue
                    actual = [row for row in actual_views.get(view_name, {}).get("rows", [])
                              if row.get("actual_feature_id") == feature_id
                              and row.get("geometry_type") == kind and row.get("semantic") == semantic_kind]
                    expected_geometry = [row["geometry"] for row in wanted]
                    actual_geometry = [row["geometry"] for row in actual]
                    report = (match_line_supports(expected_geometry, actual_geometry) if kind == "LINE"
                              else match(expected_geometry, actual_geometry, kind.lower()))
                    partitions.append({"feature_id": feature_id, "view": view_name, "geometry_type": kind,
                                       "semantic": semantic_kind, "match": report})
                    for row in wanted:
                        matches.append({"primitive_id": row["primitive_id"],
                                        "expected_feature_id": feature_id,
                                        "actual_feature_id": feature_id if report["status"] == "PASS" else None,
                                        "geometry_status": report["status"]})
    attribution = validate_feature_attribution(matches, unknown_count=semantic.get("unknown_count", 0))
    unattributed_actual = semantic.get("unattributed_count", 0)
    passed = attribution["status"] == "PASS" and unattributed_actual == 0
    return {"status": "PASS" if passed else "FAIL", "partitions": partitions,
            "expected_attribution_gate": attribution, "unknown_count": semantic.get("unknown_count", 0),
            "unattributed_count": unattributed_actual}


def run(graph, backend: dict, semantic_output_dir: Path) -> dict:
    upstream = Path(backend["external_backend_path"])
    declared = backend.get("drawing_structure", {}).get("views", [])
    refs = backend["feature_identity"]["references"]
    case_name = Path(backend["drawing_path"]).stem
    hlr = _capture_file(semantic_output_dir / f"{case_name}_hlr.slddrw", upstream, refs, declared)
    hlv = _capture_file(semantic_output_dir / f"{case_name}_hlv.slddrw", upstream, refs, declared)
    semantic = combine_semantics(hlr, hlv)
    validation = validate_attributed_roundtrip(graph, semantic)
    return {"status": validation["status"], "hlr": hlr, "hlv": hlv,
            "semantic_graph": semantic, "validation": validation}
