# B006 Phase 3.3 Real SolidWorks Final Validation

## 1. Baseline

- Repository: `zhuhhz/solidworks-main-skill`
- Branch: `feat/benchmark-006-pattern`
- Commit: `d562cfe574a50bdd063f512bbe38317b0c787383`
- Validation run: `2026-09-05T15:06:30+08:00`
- Contract domain: `PART_FEATURE_PATTERN`
- Code, contract, matcher thresholds, golden geometry, B001-B005, and the external backend were not modified during this validation.

## 2. Environment

- OS: Windows 11 (`10.0.26100`)
- Python: 3.14.5
- pytest: 9.1.1
- SolidWorks: 2024 SP04
- SolidWorks COM ProgID used by the existing adapter: `SldWorks.Application.32`
- External execution backend: third-party `wzyn20051216/solidworks-automation-skill`

The SolidWorks Skill preflight passed. `pywin32`, `comtypes`, SolidWorks registration, and the SolidWorks installation were available. Unrelated optional OCP, CalculiX, and AutoCAD warnings did not participate in B006.

## 3. Benchmark model

The bounded B006 model consists of:

1. `base_001`: 100 x 60 x 20 mm base block.
2. `seed_hole_001`: one diameter 10 mm through-hole seed at `(-35, -10)` mm in the feature plane.
3. `pattern_001`: native linear pattern with four total occurrences.
4. Occurrence positions: `(-35, -10)`, `(-15, -10)`, `(5, -10)`, and `(25, -10)` mm.

The existing pipeline executed the required chain:

`Input -> FeatureGraph -> ModelingPlan -> SolidWorks Adapter -> Native Linear Pattern -> Save -> Close -> Read-only Reopen -> Feature Tree -> B-Rep -> Ownership Evidence -> Drawing -> HLR/HLV -> Level 1 -> Level 2A -> Level 2B -> Pattern Contract Validation`

Backend result: **PASS**.

## 4. Evidence directories

The runner's generated outputs were first preserved as a unique timestamped snapshot; Phase 3.1 evidence was not overwritten. After review, the non-CAD machine evidence was promoted to the repository's canonical `case_006_pattern` paths for the B006 baseline. The complete timestamped snapshot, including ignored native CAD files, is retained in the named stash `pre-v0.6-b006-phase3-3-timestamp-evidence-local`.

- Canonical 3D/drawing evidence: `experiments/three_view_reconstruction/results/case_006_pattern/`
- Canonical HLR/HLV evidence: `experiments/hlv_hlr_semantics/results/case_006_pattern/`
- Local timestamped 3D/drawing snapshot: `experiments/three_view_reconstruction/results/case_006_pattern_phase3_3_20260905T150630/`
- Local timestamped HLR/HLV snapshot: `experiments/hlv_hlr_semantics/results/case_006_pattern_phase3_3_20260905T150630/`
- Part: `case_006_pattern.SLDPRT` (72,953 bytes)
- Drawing: `case_006_pattern.SLDDRW` (33,033 bytes)
- Part SHA-256: `55A60E59381E285380CC35082AE418D34DE40E5D16AFBBACF9276F7F5F03F996`
- Drawing SHA-256: `3F8F47B2686CF22798CE7C1889067A7410B214D33C28995589C5E7218879262A`
- Primary result: `benchmark_results.json`
- Native backend evidence: `native_backend_evidence.json`
- Pattern drawing attribution: `pattern_attributed_roundtrip.json`
- Semantic evidence: `hlr_geometry.json`, `hlv_geometry.json`, and `semantic_diff.json`
- Visual review: isometric, front, top, and right BMP captures plus the review report.

The automated visual review returned `pass`, score 100, with no detected issues. Its report correctly retains the manual-review notice because automated image checks cannot replace final engineering judgment.

The existing runner writes its working evidence to fixed `case_006_pattern` directories. The generated files were hash-verified against the timestamped snapshot before promotion. Git history and the Phase 3.1 named stash preserve the prior failed evidence; the canonical paths now contain the reviewed Phase 3.3 result rather than an unreviewed temporary run.

## 5. Feature Tree

Initial and read-only reopened Feature Tree checks both returned **PASS**.

| Order | Feature ID | SolidWorks type | Identity source |
|---:|---|---|---|
| 1 | `base_001` | `Extrusion` | `IModelDocExtension.GetPersistReference3` |
| 2 | `seed_hole_001` | `ICE` / Cut | `IModelDocExtension.GetPersistReference3` |
| 3 | `pattern_001` | `LPattern` | `IModelDocExtension.GetPersistReference3` |

Verified checks:

- Persistent feature order is correct.
- The pattern is a native SolidWorks `LPattern`, not explicit copied geometry.
- Exactly one seed feature is present.
- No pattern occurrence is skipped.
- Feature identity does not depend on feature-name matching.

## 6. Pattern definition

Initial and reopened pattern-definition probes both returned **PASS**.

| Property | Actual |
|---|---:|
| Feature type | `LPattern` |
| Total instances, including seed | 4 |
| Spacing | 20.0 mm |
| Direction | `+X` |
| Reverse direction | `false` |
| Skipped items | 0 |
| Definition source | `IFeature.GetDefinition -> ILinearPatternFeatureData` |

The returned occurrence transforms were 0, +20, +40, and +60 mm in X and were identical after read-only reopen.

## 7. B-Rep measurements

Initial and reopened measurements were equal and satisfied the Level 1 gate.

| Check | Expected | Actual | Result |
|---|---|---|---|
| Base envelope | 100 x 60 x 20 mm | 100 x 60 x 20 mm | PASS |
| Internal cylindrical faces | 4 | 4 | PASS |
| Hole diameter | 10 mm each | 10.0 mm each | PASS |
| Hole centers | X spacing 20 mm, direction +X | `(-35,-10)`, `(-15,-10)`, `(5,-10)`, `(25,-10)` mm | PASS |
| Hole axes | Z | `(0,0,1)` | PASS |
| Axial extent | 20 mm | 20.0 mm each | PASS |
| Through feature | Through all | operation evidence plus full 20 mm B-Rep extent | PASS |

B-Rep cylinder boundaries alone report `through_state=unknown`; they cannot reliably distinguish blind from through. The PASS is therefore based on the existing cross-check of the through-all feature operation with the full-thickness 20 mm cylindrical B-Rep extent, not on a B-Rep-only claim.

## 8. Ownership evidence

Ownership domain: `PART_FEATURE_PATTERN`.

| Occurrence | Feature ID | Owner | Pattern ID | Seed ID | Instance index | Ownership |
|---|---|---|---|---|---:|---|
| Seed | `instance_001` | `seed_hole_001` | `pattern_001` | `seed_hole_001` | 0 | `API_EXACT` |
| Generated 1 | `instance_002` | `pattern_001` | `pattern_001` | `seed_hole_001` | 1 | `INSTANCE_EXACT` |
| Generated 2 | `instance_003` | `pattern_001` | `pattern_001` | `seed_hole_001` | 2 | `INSTANCE_EXACT` |
| Generated 3 | `instance_004` | `pattern_001` | `pattern_001` | `seed_hole_001` | 3 | `INSTANCE_EXACT` |

Ownership distribution, both initial and reopened:

- `API_EXACT`: 1
- `INSTANCE_EXACT`: 3
- `PATTERN_ONLY`: 0
- `OWNERSHIP_UNRESOLVED`: 0

Evidence sources:

- Seed: `IFace2.GetFeature` mapped to the seed persistent reference.
- Generated instances: `IFace2.GetFeature` mapped to the pattern persistent reference, combined with `ILinearPatternFeatureData.GetTransform` and a unique exact cylindrical position.
- Feature-name matching: not used.
- Nearest-geometry ownership selection: not used.
- Face-array order ownership inference: not used.

`strict_api_exact_status` is **FAIL** for both initial and reopened evidence. This is retained as a diagnostic and is expected for SolidWorks Part Feature Pattern occurrences, which do not expose independent occurrence objects. The approved B006 `PART_FEATURE_PATTERN` gate requires seed `API_EXACT` and generated instances `API_EXACT` or `INSTANCE_EXACT`; that gate returned **PASS**.

## 9. Initial/reopen comparison

The part was saved, closed, and reopened read-only. `reopened_read_only=true`.

| Evidence | Initial | Read-only reopen | Result |
|---|---|---|---|
| Feature Tree | PASS | PASS | IDENTICAL |
| Native pattern definition | 4 x 20 mm, +X | 4 x 20 mm, +X | IDENTICAL |
| B-Rep envelope | 100 x 60 x 20 mm | 100 x 60 x 20 mm | IDENTICAL |
| Hole count/diameter/positions | 4 / 10 mm / expected positions | Same | IDENTICAL |
| Ownership domain | `PART_FEATURE_PATTERN` | `PART_FEATURE_PATTERN` | IDENTICAL |
| Ownership levels | 1 API + 3 INSTANCE | 1 API + 3 INSTANCE | IDENTICAL |
| Feature/pattern/seed/index mapping | Complete | Complete | IDENTICAL |

The `reopened_ownership_mapping` contract check returned `true`.

## 10. Drawing and roundtrip validation

Three standard drawing views were created and semantic extraction used the required provenance:

- Visible geometry: `HLR_CAPTURE`
- Hidden geometry: `HLV_MINUS_HLR`

### Level 1

**PASS**.

The base envelope, hole count, hole diameters, hole positions, axes, through extent, native pattern definition, and three-view presence all passed.

### Level 2A — vector geometry

**PASS**.

- Front: four circles matched; visible outline support IoU = 1.0.
- Top: visible outline support IoU = 1.0.
- Left: visible outline support IoU = 1.0.
- Raw SolidWorks projected geometry does not expose reliable visibility semantics, so Level 2A correctly records hidden lines as `NOT_EVALUABLE`; hidden semantics are evaluated at Level 2B through HLV-minus-HLR evidence.

### Level 2B — drawing semantics

**PASS**.

- Semantic provenance: `HLV_MINUS_HLR`.
- Hidden primitives: 10 total.
- Top hidden lines: 8/8 matched, support IoU = 1.0.
- Left hidden lines: 2/2 matched, support IoU = 1.0.
- Pattern drawing attribution: PASS.
- Shared left-view hidden projections preserve the full ownership set for all four occurrences rather than forcing a single owner.

### Attribution counts

- `UNKNOWN`: **0**
- `UNATTRIBUTED`: **0**
- Drawing rows with `API_EXACT`: 3
- Drawing rows with `INSTANCE_EXACT`: 11

## 11. Negative controls

All required negative controls returned their expected failure classification:

| Control | Expected/actual classification |
|---|---|
| Wrong count | `INSTANCE_COUNT_MISMATCH` |
| Wrong spacing | `SPACING_MISMATCH` |
| Wrong direction | `DIRECTION_MISMATCH` |
| Missing seed | `MISSING_SEED` |
| Missing instance | `INSTANCE_COUNT_MISMATCH` |
| Wrong pattern type | `PATTERN_TYPE_MISMATCH` |

## 12. Regression result

Command:

```powershell
python -m pytest -v
```

Result:

- Passed: 613
- Skipped: 15
- Deselected: 2
- Failed: 0
- Warnings: 26
- Duration: 18.25 seconds

## 13. Final decision

**B006 PASS_CANDIDATE**

All acceptance gates for the defined B006 scope passed:

- Backend: PASS
- Save/close/read-only reopen: PASS
- Feature Tree: PASS
- Native pattern definition: PASS
- B-Rep: PASS
- Part Feature Pattern ownership contract: PASS
- Level 1: PASS
- Level 2A: PASS
- Level 2B: PASS
- `UNKNOWN=0`
- `UNATTRIBUTED=0`

This decision applies only to the defined benchmark scope: one base block, one through-hole seed, and one four-occurrence native linear Part Feature Pattern. It is not a claim of general pattern reconstruction support and is not a release-level declaration of B006 PASS.
