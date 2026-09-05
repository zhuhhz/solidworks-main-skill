# B006 Phase 3 — Real SolidWorks Pattern Validation

## Status

**B006 NOT VALIDATED**

The real geometry and drawing roundtrip completed for the defined B006 scope,
but the strict ownership gate did not pass. Only the seed occurrence has direct
`API_EXACT` face ownership. The three generated occurrences have
`INSTANCE_EXACT` evidence because SolidWorks reports their cylindrical faces as
owned by the native `LPattern` feature rather than by an individual occurrence
object. The requested rule states that any non-`API_EXACT` occurrence keeps
B006 `NOT VALIDATED`.

This result applies only to:

- BaseBlock: 100 × 60 × 20 mm
- Seed: Ø10 through hole at (-35, -10) mm
- Native linear pattern: four total occurrences, 20 mm spacing, signed +X

## Environment

- OS: Windows 11
- Python: 3.14.5
- pytest: 9.1.1
- SolidWorks: 2024 SP04
- Branch: `feat/benchmark-006-pattern`
- Test entry point: `python -m pytest`
- External backend: third-party `wzyn20051216/solidworks-automation-skill`
- Third-party source changes: none

The SolidWorks skill preflight passed. CAD Studio doctor found registered
SolidWorks 2024 SP04 plus working pywin32 and comtypes.

## Backend

Result: **PASS**

The main-project adapter reused the external backend for session, sketch,
extrusion, through-hole, save/reopen, drawing, B-Rep and review operations. It
added a bounded native-pattern compatibility adapter without modifying the
third-party source.

Native pattern creation used:

```text
IFeature::Select2(mark=4) for the seed
IEntity::Select4(mark=1) for an analytic X-parallel edge
IFeatureManager::CreateDefinition(swFmLPattern=6)
ILinearPatternFeatureData.D1Spacing = 0.020 m
ILinearPatternFeatureData.D1TotalInstances = 4
IFeatureManager::CreateFeature
```

The direction entity was selected from exact analytic line direction. It was
not selected by localized name or screen coordinate.

Official API references used for the adapter design:

- `IFeatureManager::FeatureLinearPattern3` is obsolete and superseded by newer
  APIs: <https://help.solidworks.com/2024/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IFeatureManager~FeatureLinearPattern3.html>
- `ILinearPatternFeatureData` creation and selection marks:
  <https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ILinearPatternFeatureData.html>
- Pattern seed feature array:
  <https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ILinearPatternFeatureData~PatternFeatureArray.html>

## Save/Reopen

Result: **PASS**

The run performed:

1. Create part.
2. Save SLDPRT.
3. Collect initial Feature Tree, PatternFeatureData, B-Rep and ownership.
4. Close the part.
5. Reopen the SLDPRT with `read_only=True` and `silent=True`.
6. Repeat Feature Tree, PatternFeatureData, B-Rep and ownership checks.
7. Create and save the three-view SLDDRW.

Initial and reopened results agree.

## Feature Tree

Result: **PASS**

Persistent-reference order:

```text
base_001 / Extrusion
  -> seed_hole_001 / Cut
  -> pattern_001 / LPattern
```

Acceptance identity uses `IModelDocExtension.GetPersistReference3`; diagnostic
feature names are excluded. `IFeature.GetDefinition` returned:

- `D1TotalInstances = 4`
- `D1Spacing = 20.0 mm`
- `D1ReverseDirection = false`
- seed feature count = 1
- skipped instance count = 0
- generated transforms = +20, +40 and +60 mm in X

## B-Rep

Result: **PASS for geometry**

- Envelope: 100 × 60 × 20 mm
- Internal cylindrical faces: 4
- Diameter: Ø10 mm for all four
- Centers: (-35, -10), (-15, -10), (5, -10), (25, -10) mm
- Axis: Z
- Axial extent: 20 mm

The B-Rep collector correctly reports that a cylindrical face alone cannot
prove through/blind intent. Through state is cross-checked against the native
cut/pattern operation and full 20 mm axial extent.

## Ownership

Strict result: **FAIL**

| Occurrence | Direct face owner | Evidence level |
| --- | --- | --- |
| `instance_001` | `seed_hole_001` | `API_EXACT` |
| `instance_002` | `pattern_001` | `INSTANCE_EXACT` |
| `instance_003` | `pattern_001` | `INSTANCE_EXACT` |
| `instance_004` | `pattern_001` | `INSTANCE_EXACT` |

Initial and reopened counts are identical:

- `API_EXACT = 1`
- `INSTANCE_EXACT = 3`
- `OWNERSHIP_UNRESOLVED = 0`

`INSTANCE_EXACT` uses the exact chain:

```text
IFace2.GetFeature
  -> pattern persistent reference
  -> ILinearPatternFeatureData.GetTransform(api instance index)
  -> unique exact cylinder-position equality
  -> declared PatternEvidence identity
```

It does not use nearest geometry, localized names, face-array order or list
order. Nevertheless, it is weaker than direct face-to-occurrence API identity
and cannot satisfy this phase's strict `API_EXACT` gate.

## Drawing

SLDDRW generation: **PASS**

- Front view: created
- Top view: created
- Side/right physical view representing the input Left frame: created
- HLR capture: PASS
- HLV capture: PASS
- Semantic provenance: `HLV_MINUS_HLR`

The review BMPs were visually inspected. They show one rectangular plate and
four evenly spaced through holes; no missing or duplicate occurrence is visible.
The automated review score is 100, with manual review still required by policy.

## Level 1

Result: **PASS**

The envelope, four-hole count, diameters, positions, axes, through extents,
native pattern definition and three-view creation all matched the B006 contract.

## Level 2A

Result: **PASS**

Visible vector geometry matched in all views:

- Front: four outer supports and four circles
- Top: four outer supports
- Side: four outer supports

Existing matcher thresholds were not changed.

## Level 2B

Geometric/semantic result: **PASS**

- Top hidden supports: expected 8, actual 8
- Side overlapping hidden supports: expected 2, actual 2
- Semantic source: HLV minus HLR
- `UNKNOWN = 0`
- `UNATTRIBUTED = 0`

The two Side hidden supports preserve:

```json
{"ownership_set": ["instance_001", "instance_002", "instance_003", "instance_004"]}
```

They are not forced to a single owner. Drawing occurrence evidence contains
three `API_EXACT` seed primitives and eleven `INSTANCE_EXACT` primitives/shared
supports. Therefore drawing geometry attribution passes, while the strict
all-`API_EXACT` drawing gate fails.

## Negative tests

| Test | Expected | Actual |
| --- | --- | --- |
| Count wrong | `INSTANCE_COUNT_MISMATCH` | `INSTANCE_COUNT_MISMATCH` |
| Spacing wrong | `SPACING_MISMATCH` | `SPACING_MISMATCH` |
| Direction wrong | `DIRECTION_MISMATCH` | `DIRECTION_MISMATCH` |
| Seed missing | `MISSING_SEED` | `MISSING_SEED` |
| Instance missing | `INSTANCE_COUNT_MISMATCH` | `INSTANCE_COUNT_MISMATCH` |
| Pattern type wrong | `PATTERN_TYPE_MISMATCH` | `PATTERN_TYPE_MISMATCH` |

Negative-test result: **PASS**

## Evidence

- `experiments/three_view_reconstruction/results/case_006_pattern/benchmark_results.json`
- `experiments/three_view_reconstruction/results/case_006_pattern/native_backend_evidence.json`
- `experiments/three_view_reconstruction/results/case_006_pattern/pattern_attributed_roundtrip.json`
- `experiments/three_view_reconstruction/results/case_006_pattern/case_006_pattern.SLDPRT`
- `experiments/three_view_reconstruction/results/case_006_pattern/case_006_pattern.SLDDRW`
- `experiments/three_view_reconstruction/results/case_006_pattern/review/*.bmp`
- `experiments/hlv_hlr_semantics/results/case_006_pattern/hlr_geometry.json`
- `experiments/hlv_hlr_semantics/results/case_006_pattern/hlv_geometry.json`
- `experiments/hlv_hlr_semantics/results/case_006_pattern/semantic_diff.json`

Native SolidWorks binary files remain ignored by Git and are retained locally.

## Observed API issues

1. SW2024's generated COM wrapper requires an explicit by-reference error
   argument for `GetObjectByPersistReference3`. The adapter uses
   `VARIANT(VT_BYREF | VT_I4, 0)` and records the returned error code.
2. `ILinearPatternFeatureData.GetTransform` returns generated-copy transforms
   for indices 1 through `D1TotalInstances - 1`; the seed occurrence is proven
   by the seed feature reference rather than a transform call.
3. A redundant second `GetPolylines7` attribution pass caused a SW2024 COM
   stall after HLR/HLV evidence had already been saved. The final runner now
   consumes the persisted HLR/HLV vector evidence once and preserves the native
   backend JSON before the semantic stage.

## Final decision

| Gate | Result |
| --- | --- |
| Backend | PASS |
| Save/Reopen | PASS |
| Feature Tree | PASS |
| B-Rep geometry | PASS |
| Strict occurrence ownership | **FAIL** |
| Level 1 | PASS |
| Level 2A | PASS |
| Level 2B geometry/semantics | PASS |
| UNKNOWN | 0 |
| UNATTRIBUTED | 0 |

Final classification: **B006 NOT VALIDATED**.

No merge, tag, release or B006 PASS declaration is made.
