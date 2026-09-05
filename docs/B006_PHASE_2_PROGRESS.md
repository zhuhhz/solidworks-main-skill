# B006 Phase 2 — Pattern Evidence Binding

Status: **NOT VALIDATED**

This phase implements only the structured evidence and attribution contract for
the defined B006 four-hole linear pattern. It does not call SolidWorks COM and
does not constitute real CAD, B-Rep, drawing, or roundtrip validation.

## Scope

- Base block: 100 × 60 × 20 mm
- Seed: Ø10 through hole at `(-35, -10, 0)`
- Pattern: four total occurrences, 20 mm pitch, signed `+X` direction
- Instance identities: `instance_001` through `instance_004`

## Structured flow

```text
ProjectionGraph
  -> PatternEvidence
  -> explicit instance attribution
  -> PatternFeatureGraph
```

`case_006_pattern.json` contains independent projection primitive IDs, the
Phase 1 pattern contract, and evidence records that explicitly bind primitives
to occurrence identities. Coordinates are consistency checks only. The binder
does not choose an owner by nearest geometry, evidence order, feature name, or
an instance-number suffix.

## PatternEvidence

Each record carries:

- `pattern_id`
- `seed_feature_id`
- `instance_id`
- `instance_index`
- `position`
- `source_evidence_ids`
- `geometry_reference`
- `confidence`

The contract additionally records `view`, `geometry_type`, `source`, and
`ownership_set` so the attribution is auditable. Single-owner evidence requires
one exact identity, index, and 3D position. Shared projected evidence sets those
single-owner fields to `null` and retains every contributor in `ownership_set`.

## Attribution and dependency rules

- Front-view circle evidence and top-view hidden-line evidence bind explicitly
  to each occurrence.
- The claimed position must reproduce the referenced projection geometry within
  the fixed 0.01 mm contract tolerance.
- The seed occurrence must carry the explicit `seed_geometry_001` lineage anchor.
- Each instance requires one front circle and two top hidden lines.
- Feature dependencies remain `Base -> Seed -> Pattern -> Instances`; no
  instance depends directly on Base.

## Overlapping projection

All four B006 holes have the same Y position, so their left-view hidden lines
coincide. Two left-view records preserve:

```json
{"ownership_set": ["instance_001", "instance_002", "instance_003", "instance_004"]}
```

The binder neither duplicates the primitive reference nor forces it to a single
owner. An incomplete contributor set is a hard attribution failure.

## Unit tests

Command:

```powershell
python -m pytest -v tests/unit/test_b006_pattern_evidence.py
```

Result: `8 passed, 0 failed`.

Covered cases:

1. Complete four-instance evidence — PASS
2. Incorrect instance position — FAIL
3. Missing instance evidence — UNATTRIBUTED
4. Missing seed lineage — FAIL
5. Incorrect pattern count — FAIL
6. Overlapping ownership preservation — PASS
7. Swapped instance attribution — FAIL
8. Incomplete overlapping ownership set — FAIL

## Validation boundary

B006 remains **NOT VALIDATED**. SolidWorks adapter execution, save/reopen,
Feature Tree, B-Rep occurrence ownership, Level 1, Level 2A, and Level 2B remain
future phases. Existing `UPSTREAM_GAP` records remain open.
