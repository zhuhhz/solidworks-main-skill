# Benchmark 004 Plan — Off-centre Straight Through Slot

Status: planning only. This document introduces no B004 implementation, benchmark JSON, schema change, inference rule, SolidWorks call, or generated reference evidence.

## 1. New geometric capability

B001–B003 place their tested hole, boss, and slot at the part/face centre. B004 introduces exactly one new capability: **translated feature placement**. It keeps the already verified X-major straight-through-slot topology and moves its centre away from both the part origin and face centre. It does not introduce rotation, blind depth, a new primitive family, or multiple features.

Proposed canonical model geometry:

- Base block: 100 × 60 × 20 mm.
- Straight through slot: overall end-to-end length 40 mm, width 20 mm, R10 ends, centre-to-centre length 20 mm.
- Internal model centre: `(X=+15, Y=+8)` mm.
- Front drawing lower-left coordinates: `(X=65, Y=38)` mm.
- Major axis: X. Through state: true.

The slot envelope is X=−5…35 and Y=−2…18 mm in model-centred coordinates, so it remains inside the base with positive boundary clearance.

## 2. Why this is the smallest useful increment

B004 reuses B003's LINE/ARC schema, slot hypothesis, `STRAIGHT_SLOT` FeatureGraph type, through-cut plan, adapter route, B-Rep topology and ARC matcher. Only placement and cross-view coordinate evidence change. This directly tests and removes the implicit `feature centre == part origin` assumption without confounding results with arbitrary rotation or blind termination.

## 3. Expected three-view geometry

Third-angle input remains white-box structured geometry with common scale:

- Front X/Y: 100 × 60 outer rectangle; slot centred at `(65,38)`. Tangency lines run from X=55 to X=75 at Y=28 and Y=48. R10 end arcs are centred at `(55,38)` and `(75,38)`, with total slot extremes X=45 and X=85.
- Top X/Z: 100 × 20 outer rectangle. HLV evidence is expected at X=45, 55, 75 and 85, spanning the full 20 mm block depth. These supports constrain the slot's X translation.
- Side Z/Y: 20 × 60 outer rectangle. Hidden supports are expected at Y=28 and Y=48, spanning the full 20 mm depth. These supports constrain the slot's Y translation.

Coordinate contract remains `Front.X ↔ Top.X`, `Front.Y ↔ Side.Y`, and `Top.Z ↔ Side.Z`. The corrected B003 topology is the starting reference pattern, translated rather than reinterpreted.

## 4. Expected engineering semantic feature

The only confirmed feature is `STRAIGHT_SLOT`, X-major and through-all. Its hypothesis must retain evidence for two parallel lines, equal R10 semicircular ends, endpoint continuity, closure, tangency, width, translated centre, orthogonal depth and through state. A slot-like front contour alone remains `UNKNOWN_SLOT_LIKE_CONTOUR / AMBIGUOUS`.

## 5. Expected FeatureGraph representation

```json
{
  "type": "STRAIGHT_SLOT",
  "overall_length_mm": 40.0,
  "width_mm": 20.0,
  "radius_mm": 10.0,
  "center_x_mm": 15.0,
  "center_y_mm": 8.0,
  "major_axis": "X",
  "through": true
}
```

The centre is stored in the canonical model-centred frame. The FeatureGraph must not replace the slot with a rectangle and two holes or infer placement from the benchmark name.

## 6. Expected ModelingPlan

```json
{
  "operations": [
    {
      "type": "base_extrude",
      "sketch_plane": "Front Plane",
      "profile": {"type": "rectangle", "width_mm": 100, "height_mm": 60},
      "depth_mm": 20
    },
    {
      "type": "cut_extrude_through_slot",
      "sketch_plane": "Front Plane",
      "profile": {
        "type": "straight_slot",
        "overall_length_mm": 40,
        "width_mm": 20,
        "center_x_mm": 15,
        "center_y_mm": 8,
        "major_axis": "X"
      },
      "direction": "through_all"
    }
  ]
}
```

The plan is produced from the FeatureGraph. No benchmark-specific SolidWorks branch may hardcode `(15,8)`.

## 7. Expected SolidWorks feature type

Expected Feature Tree: one base extrusion followed by one named through cut whose sketch has four non-construction profile entities (two lines/two arcs) and, if produced by the current API, one construction centreline. The B003 SW2024 `UPSTREAM_GAP` remains narrowly scoped: the third-party slot helper's width semantics require the existing adapter correction. B004 must not broaden that workaround or alter third-party source.

## 8. Expected B-Rep invariants

- Overall envelope remains 100 × 60 × 20 mm.
- Exactly two internal semicylindrical end walls have R10 and cut-axis-parallel axes.
- End-wall centres are `(5,8)` and `(25,8)` mm in canonical model coordinates; spacing is 20 mm.
- Exactly two internal planar side walls lie at Y=−2 and Y=18 mm; spacing is 20 mm.
- Overall slot X extent is −5…35 mm, or 40 mm end-to-end.
- Side-wall areas and semicylindrical areas are consistent with a full-depth 20 mm cut.
- Through state requires combined creation definition, persisted Feature Tree, and topology/open-termination evidence; axial extent alone is insufficient.
- Slot faces remain internal and belong to the expected single cut/body topology.

## 9. Expected Level 1 invariants

- View extents: Front 100×60, Top 100×20, side 20×60.
- Canonical slot centre `(15,8)` maps to Front `(65,38)`.
- Length 40, width 20, R10 and X-major orientation are unchanged.
- Top support coordinates establish X translation; side support coordinates establish Y translation.
- A generated drawing contains exactly the required standard views without using view order or localized names as orientation evidence.

## 10. Expected Level 2A primitives

- Front: outer rectangle plus two translated 20 mm tangent LINE supports and two translated R10 ARC supports.
- Top and side visible geometry: rectangular outer supports.
- CIRCLE count remains zero for the slot.
- ARC matching continues to use circle support plus angular-interval union, including split/merge equivalence, gap and overflow rejection.
- All coordinates are normalized to canonical view-local millimetres without re-centring the feature itself. Bounding-box-origin removal must not erase the measured offset relative to the base outline.

## 11. Expected Level 2B hidden-line behavior

Semantics must continue to come from `HLR_CAPTURE` and `HLV_MINUS_HLR`, never from the expected reference. Expected hidden LINE support matching is Top 4/4 at X=45/55/75/85 and side 2/2 at Y=28/48, all spanning the block depth. Front hidden count is zero. `UNKNOWN projected primitives` must be zero. No centre mark or centreline annotation is required.

## 12. Required negative tests

1. Front slot centre is offset but Top supports remain centred → `INPUT_INCONSISTENT`.
2. Front Y offset conflicts with side hidden supports → `INPUT_INCONSISTENT`.
3. One orthogonal view is absent, so translated centre cannot be corroborated → `AMBIGUOUS`.
4. Through evidence is absent → `AMBIGUOUS` between through slot and unsupported recess/blind slot.
5. Slot envelope crosses the base boundary → `INPUT_INCONSISTENT` before COM execution.
6. Front centre metadata conflicts with geometry-derived centre → `INPUT_INCONSISTENT`.
7. Model is created at origin despite an inferred `(15,8)` centre → reconstruction FAIL.
8. Generated drawing is translated as a whole but feature-to-outline relative offset is unchanged → PASS, proving sheet translation invariance.
9. Normalization re-centres the slot and hides its real offset → matcher FAIL and classification as extraction/normalization bug.
10. HLV/HLR returns centred supports contrary to B-Rep and front geometry → FAIL pending evidence classification; do not silently rewrite the reference.
11. Same translated arc geometry split into multiple angular segments → `GEOMETRY_EQUIVALENT / SEGMENTATION_DIFFERENT`.
12. Real translated arc gap or overflow beyond existing thresholds → Level 2A FAIL/PARTIAL.

## 13. Failure classification

### Implementation bug

The input is internally consistent, but inference loses `(15,8)`, the plan resets it to `(0,0)`, the adapter swaps axes/units, normalization erases relative placement, B-Rep differs from the plan, or matchers reject geometrically equivalent translated support. Fix project code; do not change expected geometry.

### Input inconsistency

Front-derived centre/width/length conflicts with Top or side supports, declared dimensions conflict with primitives, or the slot leaves insufficient material/crosses the base boundary. Return `INPUT_INCONSISTENT` and do not call SolidWorks.

### Ambiguous input

The face-on contour is slot-like but orthogonal position/depth/through evidence is missing or cannot distinguish a through slot from a recess. Return `AMBIGUOUS` with candidates; do not guess.

### Invalid reference

Generated drawing and/or model disagree with expected primitives, but independent real SolidWorks API/B-Rep/topology evidence proves the implementation and physical projection agree. Archive the old reference, write a machine-readable audit, and add regression coverage before correction. Never change a reference merely to obtain PASS.

### Upstream SolidWorks/helper gap

The external backend or SW2024 API cannot execute/read the already-correct plan, or its documented parameter semantics demonstrably differ from actual API geometry. Record `UPSTREAM_GAP` with call inputs, return/exception and B-Rep evidence; use only a minimal version-bounded adapter correction. Do not modify or copy third-party source.

## Acceptance gate before implementation

B004 implementation may begin only on a new feature branch after this planning-only change is reviewed. It must preserve the pipeline:

```text
three-view evidence
  → canonical geometry
  → engineering FeatureHypothesis
  → FeatureGraph
  → ModelingPlan
  → SolidWorks execution
  → B-Rep + drawing roundtrip
```

The implementation gate will require `python -m pytest`, real SolidWorks B001–B004 execution, save/reopen, Feature Tree/B-Rep, Level 1, Level 2A, Level 2B, and UNKNOWN=0. Arbitrary rotation and blind slot depth remain explicitly deferred.
