"""SolidWorks face ownership evidence using persistent feature references.

Feature names and nearest-geometry matching are deliberately absent. Geometry
classifies the engineering role of a face; IFace2.GetFeature plus a persistent
reference proves the owning FeatureGraph identity.
"""
from __future__ import annotations

import base64
from collections import Counter
from hashlib import sha256
import math

from schemas.ownership_evidence import OwnershipEvidence
from validation.feature_attribution import validate_ownership_evidence


def _member(value, name, *args):
    member = getattr(value, name)
    if args:
        return member(*args)
    try:
        return member() if callable(member) else member
    except Exception as exc:
        message = str(exc)
        if "-2147352573" in message or "找不到成员" in message or "Member not found" in message:
            return member
        raise


def _bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return bytes(int(item) & 0xFF for item in value)


def persistent_reference(extension, entity) -> str:
    raw = _bytes(_member(extension, "GetPersistReference3", entity))
    if not raw:
        raise RuntimeError("GetPersistReference3 returned an empty reference")
    return base64.b64encode(raw).decode("ascii")


def collect_feature_references(model, feature_objects: dict[str, object]) -> dict[str, str]:
    extension = _member(model, "Extension")
    return {feature_id: persistent_reference(extension, feature)
            for feature_id, feature in feature_objects.items()}


def _feature_id(extension, feature, feature_references: dict[str, str]) -> str | None:
    if feature is None:
        return None
    try:
        reference = persistent_reference(extension, feature)
    except Exception:
        return None
    reverse = {value: key for key, value in feature_references.items()}
    return reverse.get(reference)


def _surface_geometry(face) -> dict:
    surface = _member(face, "GetSurface")
    internal = bool(_member(face, "FaceInSurfaceSense"))
    edges = list(_member(face, "GetEdges") or [])
    box = [round(float(value) * 1000.0, 6) for value in (_member(face, "GetBox") or [])]
    common = {"internal": internal, "edge_count": len(edges), "bounding_box_mm": box}
    if surface is not None and bool(_member(surface, "IsCylinder")):
        values = list(_member(surface, "CylinderParams") or [])
        if len(values) >= 7:
            radius = abs(float(values[6]))
            return common | {
                "surface_type": "CYLINDER",
                "origin_mm": [round(float(value) * 1000.0, 6) for value in values[:3]],
                "axis": [round(float(value), 9) for value in values[3:6]],
                "radius_mm": round(radius * 1000.0, 6),
                "diameter_mm": round(radius * 2000.0, 6),
                "area_mm2": round(float(_member(face, "GetArea") or 0.0) * 1_000_000.0, 6),
            }
    if surface is not None and bool(_member(surface, "IsPlane")):
        values = list(_member(surface, "PlaneParams") or [])
        if len(values) >= 6:
            return common | {
                "surface_type": "PLANE",
                "normal": [round(float(value), 9) for value in values[:3]],
                "origin_mm": [round(float(value) * 1000.0, 6) for value in values[3:6]],
                "area_mm2": round(float(_member(face, "GetArea") or 0.0) * 1_000_000.0, 6),
            }
    return common | {"surface_type": "OTHER"}


def classify_face_role(geometry: dict) -> tuple[str, str | None]:
    """Return engineering role and expected feature without deciding owner."""
    kind = geometry.get("surface_type")
    internal = geometry.get("internal") is True
    edge_count = int(geometry.get("edge_count", 0))
    if kind == "CYLINDER" and internal and edge_count == 2:
        return "HOLE_WALL", "hole_001"
    if kind == "CYLINDER" and internal and edge_count > 2:
        return "SLOT_END_WALL", "slot_001"
    if kind == "PLANE":
        normal = [abs(float(value)) for value in geometry.get("normal", [])]
        # FaceInSurfaceSense describes orientation relative to the underlying
        # surface; it does not mean that a planar face belongs to a cut.  The
        # plate's trimmed front face is reported as True by SW 2024.  A plane
        # normal to the extrusion axis is therefore a base cap, while an
        # inward-facing plane parallel to that axis is a straight-slot wall.
        if len(normal) == 3 and normal[2] >= 0.999:
            return "BASE_SURFACE", "base_001"
        if internal and len(normal) == 3 and normal[2] <= 0.001:
            return "SLOT_SIDE_WALL", "slot_001"
        if not internal:
            return "BASE_SURFACE", "base_001"
    return "OTHER", None


def collect_face_ownership(model, feature_references: dict[str, str]) -> dict:
    extension = _member(model, "Extension")
    rows = []
    for body_index, body in enumerate(_member(model, "GetBodies2", 0, False) or []):
        for face_index, face in enumerate(_member(body, "GetFaces") or []):
            geometry = _surface_geometry(face)
            role, expected_feature_id = classify_face_role(geometry)
            try:
                face_reference = persistent_reference(extension, face)
                entity_id = "face:" + sha256(base64.b64decode(face_reference)).hexdigest()[:20]
            except Exception:
                face_reference = None
                entity_id = f"face:run-local:{body_index}:{face_index}"
            try:
                owning_feature = _member(face, "GetFeature")
                actual_feature_id = _feature_id(extension, owning_feature, feature_references)
                owner_type = (str(_member(owning_feature, "GetTypeName"))
                              if owning_feature is not None else None)
            except Exception:
                actual_feature_id = owner_type = None
            rows.append({
                "entity_id": entity_id,
                "body_index": body_index,
                "face_index": face_index,
                "persistent_reference": face_reference,
                "logical_role": role,
                "expected_feature_id": expected_feature_id,
                "feature_id": actual_feature_id,
                "ownership": "API_EXACT" if actual_feature_id else "OWNERSHIP_UNRESOLVED",
                "source": "IFace2.GetFeature+IModelDocExtension.GetPersistReference3",
                "owner_type": owner_type,
                "geometry": geometry,
            })
    return validate_face_ownership_rows(rows)


def validate_face_ownership_rows(rows: list[dict]) -> dict:
    required = [row for row in rows if row.get("expected_feature_id")]
    evidence = [OwnershipEvidence(
        entity_id=row["entity_id"],
        entity_kind="FACE",
        feature_id=row.get("feature_id") if row.get("ownership") == "API_EXACT" else None,
        source=row.get("source", "IFace2.GetFeature"),
        strength=row.get("ownership", "OWNERSHIP_UNRESOLVED"),
        details={"logical_role": row.get("logical_role"), "owner_type": row.get("owner_type")},
    ) for row in required]
    expected = {row["entity_id"]: row["expected_feature_id"] for row in required}
    gate = validate_ownership_evidence(expected, evidence) if required else {
        "status": "FAIL", "unresolved_count": 0, "misattributed_count": 0,
        "reason": "no required faces were classified",
    }
    role_counts = Counter(row.get("logical_role") for row in required)
    required_counts = {"BASE_SURFACE": 6, "HOLE_WALL": 1, "SLOT_END_WALL": 2, "SLOT_SIDE_WALL": 2}
    missing_roles = {
        role: {"expected_minimum": minimum, "actual": role_counts.get(role, 0)}
        for role, minimum in required_counts.items() if role_counts.get(role, 0) < minimum
    }
    passed = gate.get("status") == "PASS" and not missing_roles
    return {
        "status": "PASS" if passed else "FAIL",
        "api": {
            "face_owner": "IFace2.GetFeature",
            "feature_identity": "IModelDocExtension.GetPersistReference3",
            "strength_required": "API_EXACT",
        },
        "rows": rows,
        "required_face_count": len(required),
        "role_counts": dict(role_counts),
        "missing_roles": missing_roles,
        "gate": gate,
    }


def build_owned_geometry_summary(ownership: dict, operations: list[dict], base_depth_mm: float) -> dict:
    rows = ownership.get("rows", [])
    exact = [row for row in rows if row.get("ownership") == "API_EXACT"
             and row.get("feature_id") == row.get("expected_feature_id")]
    hole_faces = [row for row in exact if row.get("logical_role") == "HOLE_WALL"]
    slot_ends = [row for row in exact if row.get("logical_role") == "SLOT_END_WALL"]
    slot_sides = [row for row in exact if row.get("logical_role") == "SLOT_SIDE_WALL"]
    operation_by_feature = {row.get("source_feature_id"): row for row in operations}
    holes, slots = [], []
    if len(hole_faces) == 1:
        geometry = hole_faces[0]["geometry"]
        box = geometry.get("bounding_box_mm", [])
        axial_extent = abs(box[5] - box[2]) if len(box) == 6 else None
        holes.append({
            "feature_id": "hole_001",
            "diameter_mm": geometry.get("diameter_mm"),
            "center_mm": geometry.get("origin_mm", [])[:2],
            "axis": geometry.get("axis"),
            "through": bool(operation_by_feature.get("hole_001", {}).get("evidence", {}).get("through"))
                       and axial_extent is not None and abs(axial_extent - base_depth_mm) <= 0.05,
            "axial_extent_mm": axial_extent,
            "entity_ids": [hole_faces[0]["entity_id"]],
        })
    if len(slot_ends) == 2 and len(slot_sides) >= 2:
        end_geometry = [row["geometry"] for row in slot_ends]
        centers = [item.get("origin_mm", [])[:2] for item in end_geometry]
        radius = sum(float(item.get("radius_mm", 0.0)) for item in end_geometry) / 2.0
        delta_x = abs(centers[0][0] - centers[1][0])
        delta_y = abs(centers[0][1] - centers[1][1])
        major_axis = "X" if delta_x >= delta_y else "Y"
        center_distance = max(delta_x, delta_y)
        transverse = 1 if major_axis == "X" else 0
        side_positions = sorted({round(float(row["geometry"]["origin_mm"][transverse]), 6)
                                 for row in slot_sides})
        boxes = [item.get("bounding_box_mm", []) for item in end_geometry]
        through_brep = all(len(box) == 6 and abs(abs(box[5] - box[2]) - base_depth_mm) <= 0.05 for box in boxes)
        slots.append({
            "feature_id": "slot_001",
            "overall_length_mm": center_distance + 2.0 * radius,
            "width_mm": side_positions[-1] - side_positions[0] if len(side_positions) >= 2 else None,
            "radius_mm": radius,
            "center_mm": [sum(point[0] for point in centers) / 2.0,
                          sum(point[1] for point in centers) / 2.0],
            "major_axis": major_axis,
            "through": bool(operation_by_feature.get("slot_001", {}).get("evidence", {}).get("through")) and through_brep,
            "entity_ids": [row["entity_id"] for row in slot_ends + slot_sides],
        })
    return {"holes": holes, "slots": slots, "ownership_status": ownership.get("status")}


def _feature_relations(feature) -> dict:
    types = []
    try:
        child = _member(feature, "GetFirstSubFeature")
        while child is not None:
            types.append(str(_member(child, "GetTypeName2")))
            child = _member(child, "GetNextSubFeature")
    except Exception:
        pass
    try:
        for parent in _member(feature, "GetParents") or []:
            types.append(str(_member(parent, "GetTypeName2")))
    except Exception:
        pass
    return {"related_feature_types": types, "has_profile_feature": "ProfileFeature" in types}


def collect_feature_tree_provenance(model, feature_references: dict[str, str], plan) -> dict:
    extension = _member(model, "Extension")
    reverse = {value: key for key, value in feature_references.items()}
    rows = []
    feature = _member(model, "FirstFeature")
    index = 0
    while feature is not None:
        try:
            reference = persistent_reference(extension, feature)
        except Exception:
            reference = None
        feature_id = reverse.get(reference)
        if feature_id:
            rows.append({
                "tree_index": index,
                "feature_id": feature_id,
                "type": str(_member(feature, "GetTypeName")),
                "type_name_2": str(_member(feature, "GetTypeName2")),
                "diagnostic_name": str(_member(feature, "Name")),
                "identity_source": "IModelDocExtension.GetPersistReference3",
                **_feature_relations(feature),
            })
        feature = _member(feature, "GetNextFeature")
        index += 1
    expected_order = [operation.source_feature_id for operation in plan.operations]
    actual_order = [row["feature_id"] for row in rows]
    expected_types = {
        "base_001": {"Extrusion", "Boss", "BossExtrude"},
        "hole_001": {"ICE", "Cut", "CutExtrude"},
        "slot_001": {"ICE", "Cut", "CutExtrude"},
    }
    type_ok = all(row["type"] in expected_types.get(row["feature_id"], set())
                  or row["type_name_2"] in expected_types.get(row["feature_id"], set()) for row in rows)
    sketch_ok = len(rows) == len(expected_order) and all(row["has_profile_feature"] for row in rows)
    passed = actual_order == expected_order and type_ok and sketch_ok
    return {
        "status": "PASS" if passed else "FAIL",
        "identity_source": "persistent reference; diagnostic_name excluded from acceptance",
        "expected_order": expected_order,
        "actual_order": actual_order,
        "type_check": type_ok,
        "sketch_relation_check": sketch_ok,
        "features": rows,
    }
