"""Outer feature-attribution gates for B-Rep and Level-2 evidence.

Existing geometry matchers remain untouched.  These validators consume their
results plus independently collected ownership evidence.
"""
from __future__ import annotations

from schemas.ownership_evidence import OwnershipEvidence


def validate_ownership_evidence(expected: dict[str, str],
                                actual: list[OwnershipEvidence]) -> dict:
    rows = {row.entity_id: row for row in actual}
    missing = sorted(set(expected) - set(rows))
    extra = sorted(set(rows) - set(expected))
    unresolved = [row.entity_id for row in actual
                  if row.feature_id is None or row.strength == "OWNERSHIP_UNRESOLVED"]
    misattributed = [entity_id for entity_id, feature_id in expected.items()
                     if entity_id in rows and rows[entity_id].feature_id is not None
                     and rows[entity_id].feature_id != feature_id]
    passed = not missing and not extra and not unresolved and not misattributed
    return {
        "status": "PASS" if passed else "FAIL",
        "missing_entity_ids": missing,
        "extra_entity_ids": extra,
        "unresolved_entity_ids": sorted(unresolved),
        "misattributed_entity_ids": sorted(misattributed),
        "unresolved_count": len(unresolved),
        "misattributed_count": len(misattributed),
        "evidence": [row.to_dict() for row in actual],
    }


def validate_feature_attribution(matches: list[dict], *, unknown_count: int) -> dict:
    unattributed = [row.get("primitive_id") for row in matches if not row.get("actual_feature_id")]
    misattributed = [row.get("primitive_id") for row in matches
                     if row.get("actual_feature_id") is not None
                     and row.get("actual_feature_id") != row.get("expected_feature_id")]
    geometry_failures = [row.get("primitive_id") for row in matches
                         if row.get("geometry_status") != "PASS"]
    passed = unknown_count == 0 and not unattributed and not misattributed and not geometry_failures
    return {
        "status": "PASS" if passed else "FAIL",
        "unknown_count": int(unknown_count),
        "unattributed_count": len(unattributed),
        "misattributed_count": len(misattributed),
        "geometry_failure_count": len(geometry_failures),
        "unattributed_primitive_ids": sorted(value for value in unattributed if value),
        "misattributed_primitive_ids": sorted(value for value in misattributed if value),
        "geometry_failure_primitive_ids": sorted(value for value in geometry_failures if value),
    }
