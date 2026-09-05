# Benchmark 004 Verification Report — Offset Straight Through Slot

Test date: 2026-09-05  
Repository: `zhuhhz/solidworks-main-skill`  
External execution backend: third-party `wzyn20051216/solidworks-automation-skill` (source unchanged)  
Environment: Windows 11, Python 3.14.5, pytest 9.1.1, SolidWorks 2024 SP04

## 1. Branch

Implementation and evidence were produced on `feat/benchmark-004-offset-slot`, not on `main`.

## 2. Commits

- Planning baseline: `ae122cc docs: define benchmark 004 off-centre slot plan`
- Implementation: `86b7faa feat: validate benchmark 004 offset slot placement`
- Real SolidWorks evidence: `2a2e598 test: record benchmark 004 SolidWorks quality gate`
- Final report: the documentation commit containing this file.

The pre-development baseline was `v0.4-benchmark-003` / `bce9d3d` with 517 passed, 15 skipped, 2 deselected, and 0 failed.

## 3. B004 benchmark geometry

- Base block: 100 × 60 × 20 mm.
- Feature: one X-major straight through slot.
- Overall length: 40 mm; width: 20 mm; end radius: R10; end-centre spacing: 20 mm.
- Canonical model centre: `(X=15, Y=8)` mm.
- Slot envelope in model coordinates: `X=-5…35`, `Y=-2…18` mm.
- Front-view lower-left coordinates: centre `(65,38)` mm, arc centres `(55,38)` and `(75,38)` mm.

No rotation, Y-major slot, blind termination, or new primitive/operation type was introduced.

## 4. Coordinate convention

The benchmark uses third-angle projection and a model-centred canonical frame:

- Front: X/Y; Top: X/Z; Side: Z/Y.
- `Front.X ↔ Top.X`, `Front.Y ↔ Side.Y`, `Top.Z ↔ Side.Z`.
- FeatureGraph stores the sole canonical placement as `center_x_mm=15`, `center_y_mm=8`.
- Drawing sheet position and scale are removed during view-local normalization; the feature's position relative to the part outline is preserved.

## 5. Slot placement evidence

Placement is independently supported by the front contour, Top hidden supports at X=45/55/75/85, and Side hidden supports at Y=28/48. The pipeline now rejects conflicting cross-view midpoints and a slot envelope outside the base before COM execution.

The verified chain is:

`ProjectionGraph (15,8) → FeatureGraph (15,8) → ModelingPlan (15,8) → B-Rep (15,8)`.

## 6. ProjectionGraph result

PASS. The structured input preserves the translated LINE/ARC contour and all six orthogonal hidden supports. Cross-view X and Y placement checks pass. `reference_integrity` is PASS with `history_status=ORIGINAL`; no reference correction was required.

## 7. FeatureHypothesis result

PASS / CONFIRMED as the existing `STRAIGHT_SLOT` type with confidence 1.0. Evidence comprises parallel lines, equal-radius arcs, endpoint continuity, closure, tangency, width and centre consistency, cross-view position consistency, orthogonal depth evidence, and through-state evidence. Missing cross-view evidence remains AMBIGUOUS.

## 8. FeatureGraph position

PASS. One `STRAIGHT_SLOT` is emitted with `overall_length_mm=40`, `width_mm=20`, `radius_mm=10`, `center_x_mm=15`, `center_y_mm=8`, `major_axis=X`, and `through=true`. The feature is neither re-centred nor decomposed into unrelated primitives.

## 9. ModelingPlan position

PASS. The plan contains the existing two operations:

1. `base_extrude`, 100 × 60 profile, depth 20 mm.
2. `cut_extrude_through_slot`, centre `(15,8)`, 40 × 20 mm X-major profile, `direction=through_all`.

No benchmark-specific centre is hardcoded in the SolidWorks backend path.

## 10. Adapter execution

PASS on real SolidWorks 2024 SP04. The main-project adapter converted centre `(15,8)` to slot centreline endpoints `(5,8)` and `(25,8)`, created a four-entity slot profile plus one construction centreline, created `ThroughSlot_L40_W20`, rebuilt, saved, reopened, and re-inspected the part. The resulting SLDPRT and SLDDRW are present in the B004 results directory.

## 11. Feature Tree

PASS. The persisted tree contains `BaseBlock` (`Extrusion`) followed by `ThroughSlot_L40_W20` (`ICE`) and their sketches. Acceptance combines operation evidence, feature type and B-Rep evidence; it does not rely on the feature name alone. The reopened model reports the same 21 total tree items.

## 12. B-Rep measured position

PASS after save/reopen.

- Part envelope: 100 × 60 × 20 mm.
- Internal cylindrical end-wall origins: `(5,8,-20)` and `(25,8,-20)` mm.
- Measured midpoint: `(15,8)` mm; expected midpoint: `(15,8)` mm; centre error: 0 mm.
- Diameter/R: 20/R10 mm; end-centre spacing: 20 mm; overall slot extent: 40 mm.
- Planar side-wall locations: Y=-2 and Y=18 mm; midpoint Y=8 mm; spacing 20 mm.
- Through state: PASS from creation definition, Feature Tree ownership, and B-Rep axial/topology evidence together.

## 13. Level 1

PASS. View extents are Front 100×60, Top 100×20, Side 20×60 mm. Slot dimensions and the model-local centre `(15,8)` match the B-Rep measurement with 0 mm error. A deliberately correct-shape but wrong-position model fails this gate.

## 14. Level 2A

PASS. Canonical view-local LINE and ARC support comparison retains the offset. Front visible lines and both R10 arc supports match with support/angular IoU 1.0 and no gap or overflow. A sheet translation and scales 1:1, 1:2, and 2:1 remain invariant; translated geometry at the wrong model-local position fails. Equivalent split-arc segmentation passes as geometry-equivalent while retaining segmentation information.

## 15. Level 2B

PASS using measured semantics: `HLR_CAPTURE → VISIBLE` and `HLV_MINUS_HLR → HIDDEN`. Top hidden supports match 4/4 and Side hidden supports match 2/2, each with support IoU 1.0, zero missing length, and zero overflow. Front hidden count is zero.

## 16. UNKNOWN count

`unknown_projected_primitive_count = 0`.

## 17. Negative tests

All 10 machine-readable B004 negative/invariance cases produced their expected classifications:

| Case | Expected | Actual |
| --- | --- | --- |
| X offset wrong | INPUT_INCONSISTENT | INPUT_INCONSISTENT |
| Y offset wrong | INPUT_INCONSISTENT | INPUT_INCONSISTENT |
| Mirrored model position | FAIL | FAIL |
| Accidental re-centre | FAIL | FAIL |
| Cross-view X conflict | INPUT_INCONSISTENT | INPUT_INCONSISTENT |
| Cross-view Y conflict | INPUT_INCONSISTENT | INPUT_INCONSISTENT |
| Drawing sheet translation | PASS | PASS |
| Drawing scales 1:1 / 1:2 / 2:1 | PASS | PASS |
| Equivalent different segmentation | PASS | PASS |
| Correct shape, wrong position | FAIL | FAIL |

Additional unit coverage retains AMBIGUOUS for missing cross-view evidence and INPUT_INCONSISTENT when the slot crosses the base boundary.

## 18. B001 regression

Real SolidWorks rerun PASS: Backend, save/reopen, Feature/B-Rep, Level 1, Level 2A, and Level 2B all PASS; UNKNOWN=0.

## 19. B002 regression

Real SolidWorks rerun PASS: Backend, save/reopen, Feature/B-Rep, Level 1, Level 2A, and Level 2B all PASS; UNKNOWN=0.

## 20. B003 regression

Real SolidWorks rerun PASS: Backend, save/reopen, Feature/B-Rep, Level 1, Level 2A, and Level 2B all PASS; UNKNOWN=0.

## 21. Full pytest

All commands used the required entry point, `python -m pytest`.

- Before implementation: 517 passed, 15 skipped, 2 deselected, 0 failed.
- After implementation: 531 passed, 15 skipped, 2 deselected, 0 failed; 26 warnings; 33.36 s.
- Focused B003+B004 slot suite: 31 passed.

## 22. Modified files

Core implementation changes are limited to:

- `experiments/three_view_reconstruction/benchmarks/case_004_offset_slot.json`
- `experiments/three_view_reconstruction/inference/slot_inference.py`
- `experiments/three_view_reconstruction/run_benchmark.py`
- `experiments/three_view_reconstruction/validation/negative_tests.py`
- `experiments/three_view_reconstruction/validation/reconstruction_validator.py`
- `experiments/three_view_reconstruction/validation/roundtrip_validator.py`
- `tests/unit/test_b004_offset_slot.py`
- This report and generated B001–B004 real-SolidWorks evidence.

No B001/B002/B003 benchmark golden input was changed, and no third-party source was modified.

## 23. UPSTREAM_GAP status

The known SW2024 slot-width compatibility gap remains open and narrowly contained in the `solidworks-main-skill` adapter: the external backend's `create_semicircular_slot` width semantics produce half the requested width on SolidWorks 2024. The existing adapter correction was reused without broadening or refactoring it. This remains explicitly recorded as `UPSTREAM_GAP`.

## 24. Unresolved limitations

- Final visual intent still requires human inspection of review images; the automated review score is a guardrail, not a substitute for engineering sign-off.
- Native SW2024 drawing API extraction does not directly expose all visibility semantics; Level 2B therefore uses the verified HLV-minus-HLR method.
- B-Rep cylinder boundaries alone cannot prove blind versus through; through classification deliberately requires multiple evidence sources.
- Arbitrary rotation, Y-major slots, blind slots/depths, and all B005 scope remain unimplemented and unclaimed.

## 25. Final decision

**A — B004 offset-placement semantics are complete for the defined scope.**

B004 passed real SolidWorks execution, save/reopen, Feature Tree, B-Rep placement, Level 1, Level 2A, Level 2B, and UNKNOWN=0. B001–B004 real-SolidWorks regression is fully green, and the complete pytest suite has 0 failures. The branch is eligible to establish a new B004 baseline after normal review/merge; this report does not start B005 or expand the supported geometry scope.
