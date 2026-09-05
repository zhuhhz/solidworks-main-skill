"""Real B006 pattern definition, B-Rep and occurrence ownership evidence."""
from __future__ import annotations

import base64
from hashlib import sha256
import math
import pythoncom
from win32com.client import VARIANT

from backend.ownership_probe import _member, persistent_reference


TOLERANCE_MM = 0.01


def _feature_id(extension, feature, references):
    if feature is None:
        return None
    try:
        ref = persistent_reference(extension, feature)
    except Exception:
        return None
    return {value: key for key, value in references.items()}.get(ref)


def _array(transform):
    values = list(_member(transform, "ArrayData") or []) if transform is not None else []
    return [float(value) for value in values]


def collect_pattern_definition(model, pattern_reference: str) -> dict:
    extension = _member(model, "Extension")
    error = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    feature = _member(extension, "GetObjectByPersistReference3",
                      base64.b64decode(pattern_reference), error)
    if feature is None or int(error.value) != 0:
        return {"status": "FAIL", "error": f"pattern persistent reference resolve error={error.value}"}
    try:
        data = _member(feature, "GetDefinition")
        count = int(_member(data, "D1TotalInstances"))
        spacing_mm = float(_member(data, "D1Spacing")) * 1000.0
        reverse = bool(_member(data, "D1ReverseDirection"))
        pattern_feature_count = int(_member(data, "GetPatternFeatureCount"))
        skipped = int(_member(data, "GetSkippedItemCount"))
        transforms = [{
            "api_instance_index": 0, "occurrence_role": "SEED",
            "array_data": None, "translation_mm": [0.0, 0.0, 0.0],
            "source": "seed feature persistent reference",
        }]
        # In SW2024 GetTransform is 1-based for generated copies. The seed is
        # not returned by GetTransform, despite being included in total count.
        for api_index in range(1, count):
            try:
                values = _array(_member(data, "GetTransform", api_index))
                transforms.append({
                    "api_instance_index": api_index,
                    "occurrence_role": "PATTERN_COPY",
                    "array_data": values,
                    "translation_mm": [round(values[index] * 1000.0, 6) for index in (9, 10, 11)]
                    if len(values) >= 12 else None,
                })
            except Exception as exc:
                transforms.append({"api_instance_index": api_index, "error": repr(exc)})
        return {
            "status": "PASS", "feature_type": str(_member(feature, "GetTypeName2")),
            "d1_total_instances": count, "d1_spacing_mm": spacing_mm,
            "d1_reverse_direction": reverse, "pattern_feature_count": pattern_feature_count,
            "skipped_item_count": skipped, "instance_transforms": transforms,
            "source": "IFeature.GetDefinition->ILinearPatternFeatureData",
        }
    except Exception as exc:
        return {"status": "FAIL", "error": repr(exc)}


def collect_pattern_feature_tree(model, references: dict[str, str], definition: dict) -> dict:
    extension = _member(model, "Extension")
    reverse = {value: key for key, value in references.items()}
    rows = []
    feature = _member(model, "FirstFeature")
    index = 0
    while feature is not None:
        try:
            ref = persistent_reference(extension, feature)
        except Exception:
            ref = None
        feature_id = reverse.get(ref)
        if feature_id:
            rows.append({
                "tree_index": index, "feature_id": feature_id,
                "type": str(_member(feature, "GetTypeName")),
                "type_name_2": str(_member(feature, "GetTypeName2")),
                "diagnostic_name": str(_member(feature, "Name")),
                "identity_source": "IModelDocExtension.GetPersistReference3",
            })
        feature = _member(feature, "GetNextFeature")
        index += 1
    actual = [row["feature_id"] for row in rows]
    expected = ["base_001", "seed_hole_001", "pattern_001"]
    pattern_type = next((row["type_name_2"] for row in rows if row["feature_id"] == "pattern_001"), None)
    checks = {
        "persistent_order": actual == expected,
        "native_linear_pattern_type": pattern_type in {"LPattern", "LinearPattern"},
        "definition_count": definition.get("d1_total_instances") == 4,
        "definition_spacing": abs(float(definition.get("d1_spacing_mm", -1)) - 20.0) <= TOLERANCE_MM,
        "one_seed_feature": definition.get("pattern_feature_count") == 1,
        "no_skipped_instances": definition.get("skipped_item_count") == 0,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "expected_order": expected, "actual_order": actual, "features": rows}


def _cylinder(face):
    surface = _member(face, "GetSurface")
    if surface is None or not bool(_member(surface, "IsCylinder")):
        return None
    values = list(_member(surface, "CylinderParams") or [])
    if len(values) < 7:
        return None
    radius = abs(float(values[6]))
    if abs(radius * 2000.0 - 10.0) > TOLERANCE_MM:
        return None
    box = [float(value) * 1000.0 for value in (_member(face, "GetBox") or [])]
    return {
        "center_mm": [round(float(values[0]) * 1000.0, 6), round(float(values[1]) * 1000.0, 6)],
        "axis": [round(float(value), 9) for value in values[3:6]],
        "diameter_mm": round(radius * 2000.0, 6),
        "bounding_box_mm": [round(value, 6) for value in box],
        "internal": bool(_member(face, "FaceInSurfaceSense")),
    }


def _unique_exact_position(center, instances):
    matches = [item for item in instances if math.dist(center, item.center_mm[:2]) <= TOLERANCE_MM]
    return matches[0] if len(matches) == 1 else None


def collect_pattern_ownership(model, references: dict[str, str], graph, definition: dict,
                              *, ownership_domain: str) -> dict:
    """Classify only direct API ownership as API_EXACT.

    A pattern-owned face can be linked to a unique occurrence using the native
    pattern transform plus exact cylinder position. That is INSTANCE_EXACT,
    deliberately weaker than a direct face-to-occurrence API identity.
    """
    extension = _member(model, "Extension")
    rows = []
    for body_index, body in enumerate(_member(model, "GetBodies2", 0, False) or []):
        for face_index, face in enumerate(_member(body, "GetFaces") or []):
            geometry = _cylinder(face)
            if geometry is None or not geometry["internal"]:
                continue
            try:
                encoded = persistent_reference(extension, face)
                entity_id = "face:" + sha256(base64.b64decode(encoded)).hexdigest()[:20]
            except Exception:
                encoded = None
                entity_id = f"face:run-local:{body_index}:{face_index}"
            owner = _member(face, "GetFeature")
            owner_id = _feature_id(extension, owner, references)
            instance = _unique_exact_position(geometry["center_mm"], graph.instances)
            if owner_id == graph.seed.feature_id and instance is not None and instance.instance_index == 0:
                strength = "API_EXACT"
                instance_id = instance.feature_id
                source = "IFace2.GetFeature->seed persistent reference"
            elif owner_id == graph.pattern.feature_id and instance is not None:
                strength = "INSTANCE_EXACT"
                instance_id = instance.feature_id
                source = ("IFace2.GetFeature->pattern persistent reference + "
                          "ILinearPatternFeatureData.GetTransform + unique exact cylinder position")
            else:
                strength = "OWNERSHIP_UNRESOLVED"
                instance_id = None
                source = "IFace2.GetFeature; no direct occurrence identity"
            rows.append({
                "entity_id": entity_id, "persistent_reference": encoded,
                "owner_feature_id": owner_id, "instance_id": instance_id,
                "instance_index": instance.instance_index if instance else None,
                "ownership": strength, "source": source, "geometry": geometry,
                # Canonical B006 evidence fields. Legacy aliases above remain
                # for existing drawing attribution consumers.
                "feature_id": instance_id,
                "pattern_id": graph.pattern.feature_id,
                "seed_id": graph.seed.feature_id,
                "ownership_level": strength,
            })
    ids = [row["instance_id"] for row in rows if row["instance_id"]]
    unresolved = sum(row["ownership"] == "OWNERSHIP_UNRESOLVED" for row in rows)
    api_exact = sum(row["ownership"] == "API_EXACT" for row in rows)
    instance_exact = sum(row["ownership"] == "INSTANCE_EXACT" for row in rows)
    coverage = set(ids) == {item.feature_id for item in graph.instances} and len(rows) == 4
    geometry_pass = coverage and all(
        row["geometry"]["diameter_mm"] == 10.0
        and abs(abs(row["geometry"]["axis"][2]) - 1.0) <= 1e-6
        and len(row["geometry"]["bounding_box_mm"]) == 6
        and abs(abs(row["geometry"]["bounding_box_mm"][5] - row["geometry"]["bounding_box_mm"][2]) - 20.0) <= .05
        for row in rows)
    strict_api_exact = coverage and api_exact == 4 and unresolved == instance_exact == 0
    return {
        "ownership_domain": ownership_domain,
        "status": "PASS" if geometry_pass and unresolved == 0 else "FAIL",
        "strict_api_exact_status": "PASS" if strict_api_exact else "FAIL",
        "rows": rows, "instance_coverage": coverage, "geometry_status": "PASS" if geometry_pass else "FAIL",
        "api_exact_count": api_exact, "instance_exact_count": instance_exact,
        "unresolved_count": unresolved,
        "acceptance_rule": ("PART_FEATURE_PATTERN requires seed API_EXACT and generated "
                            "occurrences API_EXACT or INSTANCE_EXACT"),
        "name_matching_used": False, "nearest_geometry_used": False, "face_array_order_used": False,
        "pattern_definition_source": definition.get("source"),
    }
