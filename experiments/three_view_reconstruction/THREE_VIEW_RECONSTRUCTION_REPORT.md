# Three-view → SolidWorks 3D Reconstruction Report

Date: 2026-09-04. Branch: `feat/benchmark-003-slot`. Scope: deterministic structured-input Benchmarks 001–003. No OCR, vision model, LLM, B004, or production-module refactor was used.

## 1. Baseline pytest result

Before B003 implementation, `python -m pytest -v` completed with **500 passed, 15 skipped, 2 deselected, 0 failed**.

## 2. B003 reference

The corrected [case_003_straight_slot.json](benchmarks/case_003_straight_slot.json) defines a 100 × 60 × 20 mm block and a centred X-major straight through slot: end-to-end length 40 mm, width 20 mm, R10 ends, centre-to-centre length 20 mm. The original top-view reference omitted two tangent hidden supports and is retained under `benchmarks/archive/`; see [B003 reference audit](../../docs/B003_REFERENCE_AUDIT.md).

## 3. ARC schema

`Arc` contains centre, radius, start/end angles and explicit `CW`/`CCW`. Units are degrees, zero is +X, angles normalize to `[0,360)`, radius must be positive, and zero/full-circle sweeps are rejected because a full circle has its own schema.

## 4. Slot FeatureHypothesis

Confirmation requires two parallel lines, two equal-radius semicircular arcs, endpoint continuity, closure, tangency, width/centre consistency, orthogonal depth evidence and explicit through evidence. B003 produced `STRAIGHT_SLOT`, confidence `1.0` from complete 9/9 evidence with no contradictions. Missing depth or through-state evidence produces `UNKNOWN_SLOT_LIKE_CONTOUR / AMBIGUOUS`.

## 5. FeatureGraph

The graph preserves one engineering-semantic `STRAIGHT_SLOT`; it is not represented as a rectangle plus two holes. Values are `overall_length_mm=40`, `width_mm=20`, `radius_mm=10`, internal centre `(0,0)`, major axis X, through true.

## 6. ModelingPlan

The serializable plan contains `base_extrude` followed by `cut_extrude_through_slot`. The slot profile retains end-to-end length semantics and `direction=through_all`.

## 7. SolidWorks execution evidence

Real SolidWorks 2024 SP04 execution passed. The adapter created, rebuilt, saved and reopened the SLDPRT, then created and saved a three-view SLDDRW. The slot sketch contains five entities: four non-construction profile entities (two lines/two arcs) plus one construction centreline. API evidence records the requested width, R10-derived centre spacing, Through All state and feature name.

One evidence-backed `UPSTREAM_GAP` remains: third-party `create_semicircular_slot(width=20)` produced an actual 10 mm-wide/R5 slot on SW2024 because its wrapper halves the value before `CreateSketchSlot`. The main project adapter uses the third-party `sketch_slot` and `extrude_cut` primitives with corrected width semantics; no third-party source was modified or copied.

## 8. Feature Tree

Save/reopen inspection contains `BaseBlock` (`Extrusion`) and `ThroughSlot_L40_W20` (`ICE`) plus their sketches. Both named features persist after reopening.

## 9. B-Rep result

PASS: envelope 100 × 60 × 20 mm; two internal semicylindrical end walls at R10; centre spacing 20 mm; overall slot extent 40 mm; axes parallel to cut Z; two internal planar side walls at Y=−10/+10 mm with 20 mm spacing and about 400 mm² each. Through state passes only from combined creation evidence, persisted Feature Tree and full-depth topology—not axial length alone.

## 10. Level 1

PASS: Front 100×60, Top 100×20, side 20×60; slot length/width/centre invariants and three generated drawing views all match.

## 11. Level 2A

PASS. Actual front drawing extraction contains six lines and two R10 semicircular arcs. Line support IoU and arc angular IoU are 1.0 with zero missing span, overflow, gap or endpoint error. The ARC matcher groups by circle support and compares unioned angular intervals, so one 180° arc equals two contiguous 90° arcs while retaining `SEGMENTATION_DIFFERENT`.

## 12. Level 2B

PASS using only real `HLR_CAPTURE` and `HLV_MINUS_HLR` provenance. Expected-vs-actual hidden line supports pass at IoU 1.0: Front 0/0, Top 4/4, side 2/2.

## 13. UNKNOWN count

`unknown_projected_primitive_count = 0`. Slot geometry does not create a centre mark or centreline annotation, and none was required.

## 14. Negative tests

All ten required guards pass: missing orthogonal depth → AMBIGUOUS; 20/18 width conflict → INPUT_INCONSISTENT; R10/R9 → INPUT_INCONSISTENT; non-tangent junction → INPUT_INCONSISTENT; open contour → INPUT_INCONSISTENT; unresolved blind/through → AMBIGUOUS; split arc support → equivalent; true angular gap → FAIL; true overflow → FAIL; wrong centre → INPUT_INCONSISTENT.

## 15. B001 regression

Real SW2024 rerun: Backend PASS, B-Rep PASS, Level 1 PASS, Level 2A PASS, Level 2B PASS, UNKNOWN 0.

## 16. B002 regression

Real SW2024 rerun: Backend PASS, B-Rep PASS, Level 1 PASS, Level 2A PASS, Level 2B PASS, UNKNOWN 0.

## 17. Full pytest result

Final `python -m pytest -v`: **517 passed, 15 skipped, 2 deselected, 0 failed** in 33.65 s. The project-standard command remains `python -m pytest`.

## 18. Modified areas

Changes are isolated to the reconstruction experiment, HLV/HLR experiment, B003 benchmark/audit, tests and generated evidence. External `wzyn20051216/solidworks-automation-skill` remains an execution dependency only.

## 19. Commits

Small commits on `feat/benchmark-003-slot` record contract/schema/inference, adapter/B-Rep, ARC/semantic roundtrip, and report/evidence. No merge or tag is performed in this task.

## 20. Limitations

Only structured input and one centred X-major straight through slot are verified. Blind slots, arbitrary slot orientation, multiple slots, slot dimensions/annotations, OCR/image parsing and generalized sketch inference remain unsupported. The upstream slot helper’s SW2024 width semantics remain a documented gap. The B-Rep half-cylinder axial metric requires semicircle-aware interpretation.

## 21. Final decision

**B — the original B003 projection reference was invalid, an evidence-backed correction was archived/audited, and the corrected benchmark now passes the complete quality gate.**

B001, B002 and corrected B003 each pass real SolidWorks Backend, save/reopen, Feature Tree/B-Rep, Level 1, Level 2A and Level 2B with UNKNOWN=0.
