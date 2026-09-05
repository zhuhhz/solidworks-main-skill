# Benchmark 005 Plan — Multi-Feature Interaction

Status: planning only. This document adds no B005 benchmark JSON, schema implementation, inference rule, matcher change, test, SolidWorks call, generated reference, or golden-data modification.

Baseline: `v0.4-benchmark-004` / merge commit `9167a05`. B001–B004 remain frozen and must continue to pass their real SolidWorks 2024 SP04 gates.

## 1. Benchmark purpose

B005 is the smallest controlled transition from single-target reconstruction to multi-feature reconstruction. It combines two already validated subtractive feature families on one base:

- one cylindrical through hole, reusing the B001/B002 feature type and operation;
- one translated X-major straight through slot, reusing B004 geometry and placement semantics.

The new capability is interaction at the engineering-representation level, not a new geometric primitive. B005 must prove that coexisting features retain separate identity, evidence, dependencies, modeling operations, B-Rep ownership, and drawing semantics.

The required pipeline remains:

```text
ProjectionGraph
  → per-feature evidence binding
  → FeatureHypotheses
  → FeatureGraph dependency DAG
  → ModelingPlan operation DAG + deterministic topological order
  → external SolidWorks execution backend through the main-project adapter
  → persisted Feature Tree + B-Rep ownership
  → regenerated drawing
  → Level 1 + attributed Level 2A + attributed Level 2B
```

An aggregate geometric match is insufficient: the hole may not consume slot evidence, and a hole/slot ownership swap must fail even when the union of projected geometry is unchanged.

## 2. Geometry definition

### 2.1 Canonical model geometry

- BaseBlock: 100 × 60 × 20 mm.
- Coordinate frame: model-centred X/Y millimetres; +Z is the extrusion direction.
- Projection: third angle; Front X/Y, Top X/Z, Side Z/Y.
- Hole: Ø20, centre `(-25,-10)` mm, axis Z, through-all.
- Slot: B004 X-major straight through slot, 40 mm overall length, 20 mm width, R10 ends, centre `(15,8)` mm, through-all.

The hole envelope is X=`-35…-15`, Y=`-20…0`. The slot envelope is X=`-5…35`, Y=`-2…18`. The two cut volumes are disjoint with 10 mm minimum X clearance. This deliberately avoids Boolean intersection in the first multi-feature benchmark, so identity and ownership can be audited without introducing a new interacting-topology problem.

### 2.2 Front-view contract

Lower-left view-local coordinates map model `(0,0)` to drawing `(50,30)`:

- outer rectangle: 100 × 60 mm;
- hole circle: centre `(25,20)`, diameter 20 mm;
- slot: centre `(65,38)`, tangent lines X=`55…75` at Y=`28` and `48`, R10 arc centres `(55,38)` and `(75,38)`, extremes X=`45…85`;
- one required `CENTERMARK` for the hole; no slot centre annotation is required.

The hole and slot front contours do not touch or overlap.

### 2.3 Top-view contract

- outer rectangle: 100 × 20 mm;
- hole hidden supports: X=`15` and `35`, each spanning Z=`0…20`;
- slot hidden supports: X=`45`, `55`, `75`, and `85`, each spanning Z=`0…20`.

All six supports are distinct. Their feature attribution is part of the reference contract, not inferred from list order.

### 2.4 Side-view contract

- outer rectangle: 20 × 60 mm;
- hole hidden supports: Y=`10` and `30`, each spanning Z=`0…20`;
- slot hidden supports: Y=`28` and `48`, each spanning Z=`0…20`.

The Y=`28` and Y=`30` supports intentionally remain close but geometrically distinct under the existing 0.10 mm line-support tolerance. The tolerance must not be widened to simplify attribution.

## 3. FeatureGraph contract

B005 must reuse the existing `BaseBlock`, `Hole`, and `StraightSlot` feature types. It must not add a new CAD feature family. The planned additive identity fields are:

- `feature_id`: stable within the graph and independent of localized SolidWorks names;
- `coordinate_system`: explicit canonical frame identifier;
- `depends_on`: feature IDs, never feature names;
- `source_evidence_ids`: ProjectionGraph evidence assigned to this feature.

The canonical graph is conceptually:

```json
{
  "base_block": {
    "feature_id": "base_001",
    "type": "BASE_BLOCK",
    "width_mm": 100,
    "height_mm": 60,
    "depth_mm": 20,
    "coordinate_system": "MODEL_CENTERED_XY_MM",
    "depends_on": []
  },
  "holes": [{
    "feature_id": "hole_001",
    "type": "THROUGH_HOLE",
    "diameter_mm": 20,
    "center_x_mm": -25,
    "center_y_mm": -10,
    "axis": "Z",
    "through": true,
    "coordinate_system": "MODEL_CENTERED_XY_MM",
    "depends_on": ["base_001"],
    "source_evidence_ids": ["front_hole_circle_001", "top_hole_hidden_pair_001", "side_hole_hidden_pair_001"]
  }],
  "slots": [{
    "feature_id": "slot_001",
    "type": "STRAIGHT_SLOT",
    "overall_length_mm": 40,
    "width_mm": 20,
    "radius_mm": 10,
    "center_x_mm": 15,
    "center_y_mm": 8,
    "major_axis": "X",
    "through": true,
    "coordinate_system": "MODEL_CENTERED_XY_MM",
    "depends_on": ["base_001"],
    "source_evidence_ids": ["front_slot_contour_001", "top_slot_hidden_set_001", "side_slot_hidden_pair_001"]
  }]
}
```

There must be one canonical storage location for each placement. Datum-relative input, if introduced later, must be converted before FeatureGraph construction rather than stored alongside absolute centre coordinates.

Feature hypotheses must reference the resulting `feature_id`. Confidence remains evidence-derived per feature; evidence from one feature cannot raise another feature's confidence.

## 4. Dependency contract

The required dependency DAG is:

```text
base_001
├── hole_001
└── slot_001
```

Rules:

1. Every non-base feature must resolve at least one valid parent.
2. The graph must be acyclic and all IDs must be unique.
3. `hole_001` and `slot_001` both depend directly on `base_001`; neither depends on the other because their cut volumes are disjoint.
4. A missing parent, floating cut, self-dependency, dependency cycle, or cut ordered before its required base is `FAIL / DEPENDENCY_VIOLATION`.
5. Dependency validity is structural and geometric; a string such as `depends_on=["BaseBlock"]` is not sufficient without resolving the referenced feature ID and validating the target body/support.

The canonical serialization is Base → Hole → Slot. However, Hole and Slot are independent siblings. A deliberately reordered but declared and valid Base → Slot → Hole plan is geometrically acceptable as `PASS_WITH_WARNING / ORDER_VARIANT_EQUIVALENT`, provided save/reopen, ownership, feature parameters, and final B-Rep all match. It is not a dependency failure. B005's own generated baseline must nevertheless use the canonical deterministic order and produce no ordering warning.

If the persisted Feature Tree differs from the recorded executed plan rather than from an explicitly declared alternative plan, the result is `FAIL / EXECUTION_PROVENANCE_MISMATCH`.

## 5. ModelingPlan contract

The operation schema should gain additive identity/provenance fields without adding new operation types:

- `operation_id`;
- `source_feature_id`;
- `depends_on_operation_ids`;
- existing profile and direction fields.

Expected canonical plan:

```json
{
  "operations": [
    {
      "operation_id": "op_base_001",
      "source_feature_id": "base_001",
      "type": "base_extrude",
      "depends_on_operation_ids": [],
      "sketch_plane": "Front Plane",
      "profile": {"type": "rectangle", "width_mm": 100, "height_mm": 60},
      "depth_mm": 20
    },
    {
      "operation_id": "op_hole_001",
      "source_feature_id": "hole_001",
      "type": "cut_extrude_through_circle",
      "depends_on_operation_ids": ["op_base_001"],
      "sketch_plane": "Front Plane",
      "profile": {"type": "circle", "diameter_mm": 20, "center_x_mm": -25, "center_y_mm": -10},
      "direction": "through_all"
    },
    {
      "operation_id": "op_slot_001",
      "source_feature_id": "slot_001",
      "type": "cut_extrude_through_slot",
      "depends_on_operation_ids": ["op_base_001"],
      "sketch_plane": "Front Plane",
      "profile": {"type": "straight_slot", "overall_length_mm": 40, "width_mm": 20, "radius_mm": 10, "center_x_mm": 15, "center_y_mm": 8, "major_axis": "X"},
      "direction": "through_all"
    }
  ]
}
```

The planner must use a validated topological sort with a stable type/ID tie-breaker, not Python list concatenation or feature names as the semantic ordering rule. Every operation must consume FeatureGraph parameters; no B005 coordinates may be hardcoded in the adapter.

## 6. SolidWorks validation plan

The real SolidWorks 2024 SP04 gate must execute only through the existing main-project adapter and third-party external backend boundary. The third-party source must remain unchanged.

Required execution evidence:

- base, hole, and slot operation inputs including `operation_id` and `source_feature_id`;
- sketch plane and sketch-entity summaries for both cuts;
- API return/feature object checks;
- deterministic feature names used only as diagnostic labels, not identities;
- rebuild result;
- SLDPRT save, close, read-only reopen, and second inspection;
- regenerated third-angle SLDDRW and drawing-structure inspection;
- front/top/right/isometric review images and review report.

Expected persisted Feature Tree for the canonical run:

```text
BaseBlock (Extrusion)
→ ThroughHole_D20 (cut feature)
→ ThroughSlot_L40_W20 (cut feature)
```

Tree acceptance combines feature type, associated sketch/profile, recorded operation provenance, dependency/topological position, and B-Rep ownership. A matching name alone cannot pass. The real B005 baseline requires the canonical order; the independent-sibling order-variant rule is tested separately.

## 7. B-Rep validation plan

### 7.1 Geometry invariants

- one solid body;
- envelope 100 × 60 × 20 mm;
- one internal Ø20 cylindrical hole face centred at `(-25,-10)`, axis parallel to Z;
- two internal R10 semicylindrical slot end faces centred at `(5,8)` and `(25,8)`;
- slot end-centre midpoint `(15,8)`, spacing 20 mm, overall extent 40 mm;
- slot planar side faces at Y=`-2` and `18`, spacing 20 mm;
- hole and slot feature volumes remain disjoint;
- through state for each cut requires creation definition, persisted Feature Tree, and B-Rep termination/axial evidence together.

### 7.2 Ownership evidence

Each measured face record must include:

- a stable run-local face/topology identifier;
- geometry classification and parameters;
- owning feature ID resolved through operation/tree mapping;
- SolidWorks evidence source, preferably `IFace2.GetFeature` or feature-owned face enumeration;
- ownership strength: `API_EXACT`, `BREP_GEOMETRY_CORRELATED`, or `UNRESOLVED`.

Expected ownership:

- Base outer planar faces → `base_001`;
- the full cylindrical hole wall → `hole_001`;
- both slot semicylindrical end walls and both slot planar side walls → `slot_001`.

B005 cannot pass ownership if the hole wall is assigned to `slot_001`, slot walls are assigned to `hole_001`, any required internal face is unresolved, or ownership is inferred only from localized feature names. Save/reopen ownership must match the initial inspection.

## 8. Level 1 criteria

Level 1 passes only when all of the following pass by feature identity:

- input view extents: Front 100×60, Top 100×20, Side 20×60 mm;
- exactly one expected hole and one expected slot;
- hole Ø20 at model `(-25,-10)` / Front `(25,20)`, axis Z, through-all;
- slot 40 × 20 R10 at model `(15,8)` / Front `(65,38)`, X-major, through-all;
- FeatureGraph → ModelingPlan parameter preservation for both features;
- actual B-Rep parameters and positions for both features;
- three regenerated standard views.

The current positional `zip(features.holes, front.circles)` behavior is insufficient for multi-feature acceptance. B005 planning requires ID/evidence-based matching and explicit missing/extra/duplicate reporting.

## 9. Level 2A criteria

Existing geometry algorithms remain unchanged:

- LINE: Infinite Support Line + Interval Coverage;
- CIRCLE: centre/radius matching;
- ARC: Circle Support + Angular Interval Coverage;
- current tolerances and gap/overflow gates.

B005 adds attribution around, not inside, these matchers. Expected and extracted primitives must be partitioned or linked by `feature_id` before per-feature reports are aggregated.

Required results:

- Front Base outline, hole circle, slot tangent lines, and slot arcs all match;
- Top hole hidden pair and four slot hidden supports match at their distinct positions;
- Side hole hidden pair and slot hidden pair match despite the 2 mm nearest-support separation;
- no missing or extra primitive within any feature partition;
- aggregate geometry correct but feature attribution swapped → FAIL;
- sheet translation and 1:1/1:2/2:1 scaling preserve view-local feature placement and attribution;
- segmentation-equivalent supports remain `GEOMETRY_EQUIVALENT / SEGMENTATION_DIFFERENT` and retain the same owner.

Actual primitive attribution should first use drawing-edge/topology correspondence (`GetPolylines7` entity → adjacent faces → owning feature). Where SolidWorks supplies only a silhouette, a unique correlation to already feature-owned B-Rep geometry may be reported as `BREP_GEOMETRY_CORRELATED`. `UNRESOLVED` attribution cannot satisfy the B005 feature-attribution gate.

## 10. Level 2B criteria

Semantic provenance remains unchanged:

- `HLR_CAPTURE → VISIBLE`;
- `HLV_MINUS_HLR → HIDDEN`;
- annotations remain separate (`CENTERMARK`, `CENTERLINE`);
- `UNKNOWN projected primitives = 0`.

B005 additionally requires `UNATTRIBUTED projected primitives = 0` for all feature-bearing supports. The expected semantic partitions are:

- Front: hole circle and slot contour VISIBLE; Base outline VISIBLE;
- Top: two hole supports HIDDEN and four slot supports HIDDEN;
- Side: two hole supports HIDDEN and two slot supports HIDDEN;
- Front hole CenterMark: `CENTERMARK` owned by/targeting `hole_001`;
- no required slot CenterMark or CenterLine.

Visibility class may never be copied from the reference. Feature ownership may never be assigned merely by nearest expected support when multiple candidates fall inside tolerance; ambiguity must remain `UNRESOLVED` and prevent PASS.

## 11. Negative tests

Implementation should later create `tests/unit/test_b005_multi_feature.py`; it is intentionally not created during planning. Required tests include:

| Case | Test input/mutation | Expected result |
| --- | --- | --- |
| Slot position wrong | Hole correct; slot model/B-Rep centre shifted | FAIL |
| Hole diameter wrong | Actual hole differs from Ø20 | FAIL |
| Hole missing | Slot correct; no hole node/operation/B-Rep | FAIL |
| Floating hole | `hole_001.depends_on=[]` | FAIL / DEPENDENCY_VIOLATION |
| Cut before base | operation dependency/order invalid | FAIL / DEPENDENCY_VIOLATION |
| Dependency cycle | Base/cut IDs form a cycle | FAIL / DEPENDENCY_CYCLE |
| Duplicate feature ID | Hole and Slot share an ID | FAIL / DUPLICATE_FEATURE_ID |
| Swapped B-Rep ownership | Hole wall attributed to Slot and slot walls to Hole | FAIL |
| Aggregate geometry, swapped projection ownership | union matches but per-feature primitive partitions are exchanged | FAIL |
| Front/Top hole conflict | circle X differs from hole hidden-pair midpoint | INPUT_INCONSISTENT |
| Front/Side slot conflict | slot Y differs from side hidden-pair midpoint | INPUT_INCONSISTENT |
| Hole borrows slot evidence | hole confirmed only because slot hidden supports exist | AMBIGUOUS, not CONFIRMED |
| One feature lacks orthogonal evidence | other feature remains valid | AMBIGUOUS for the unsupported feature; backend not called |
| Independent sibling order swapped | declared Base → Slot → Hole; geometry/ownership equal | PASS_WITH_WARNING / ORDER_VARIANT_EQUIVALENT |
| Persisted tree differs from executed plan | recorded Base → Hole → Slot, actual tree swapped | FAIL / EXECUTION_PROVENANCE_MISMATCH |
| Drawing sheet movement | same local geometry/owners, moved views | PASS |
| Drawing scales | 1:1, 1:2, 2:1 | PASS |
| Equivalent segmentation | same owned supports, different splits | PASS + SEGMENTATION_DIFFERENT |
| Hidden primitive owner unresolved | geometry and HIDDEN semantic correct, owner unknown | FAIL attribution gate |

Every negative result must be machine-readable and preserve stage classification. Expected data must not be modified to turn failures into passes.

## 12. Reference integrity and known limitations

### 12.1 Reference integrity workflow

A mismatch must be investigated in this order:

1. structured input and dimensions;
2. primitive-to-feature evidence binding;
3. cross-view coordinates;
4. FeatureGraph identities/dependencies;
5. ModelingPlan topology and order;
6. adapter inputs and operation provenance;
7. persisted Feature Tree;
8. B-Rep geometry and ownership;
9. drawing extraction/normalization;
10. Level 2 geometry and attribution;
11. HLR/HLV semantics.

Only independent real SolidWorks topology evidence may establish `REFERENCE_INVALID`. The old reference must then be archived verbatim with a machine-readable audit and regression. A mismatch is never permission to edit golden data or relax a matcher.

### 12.2 Known limitations

- This plan covers two disjoint subtractive features on one BaseBlock; it does not cover intersecting cuts, feature-created support faces, or parent-child cuts.
- Exact face ownership after save/reopen has not yet been proven for every SolidWorks face/silhouette class. B005 implementation must probe it before claiming PASS.
- The current ProjectionGraph `HiddenLinePair` has no evidence ID or owner field; a compatible attribution layer/schema addition is required.
- Current hole inference treats the presence of any Top and Side hidden pair as support. It must be made correspondence-specific so slot evidence cannot confirm the hole.
- Current Level 2 matching is aggregate by primitive type. Per-feature attribution and unresolved-owner reporting are required around the existing matchers.
- Current FeatureGraph and ModelingOperation schemas lack IDs and dependencies. Additive migration must preserve B001–B004 serialization/behavior or provide explicit version compatibility.
- The SW2024 `create_semicircular_slot` width-semantics `UPSTREAM_GAP` remains open and isolated in the main-project adapter.
- Rotated/Y-major/blind slots, blind holes, fillets, chamfers, patterns, revolve, shell, OCR, vision, and LLM inference remain out of scope.
- Final generated-view intent still requires human review.

## 13. Implementation boundary and entry gate

### Planning-only boundary

This planning change may add only this document. It must not:

- create the B005 benchmark JSON or tests;
- edit schemas, parser, inference, planner, backend, adapter, validators, matchers, tolerances, or generated evidence;
- edit B001–B004 inputs, results, reports, or archived references;
- modify the third-party `wzyn20051216/solidworks-automation-skill` source;
- start any excluded feature family.

### Planned implementation sequence

After plan review, a separate implementation branch may proceed test-first:

1. define stable feature/evidence/operation identity and dependency tests;
2. add backward-compatible schema metadata and DAG validation;
3. bind hole and slot evidence independently across views;
4. produce the deterministic topological ModelingPlan;
5. propagate operation/feature IDs through adapter evidence without changing third-party source;
6. probe and implement real B-Rep face ownership with save/reopen checks;
7. add per-feature Level 1 validation;
8. add drawing primitive attribution around existing Level 2A matchers;
9. add attributed HLR/HLV Level 2B and CenterMark validation;
10. run B005 real SolidWorks evidence and then B001–B005 full regression using `python -m pytest`.

### Readiness decision

**Planning decision: READY FOR REVIEW, then conditionally ready for B005 implementation.**

The geometry, dependency semantics, deterministic plan, order-variant classification, ownership evidence levels, Level 1/2A/2B gates, and negative cases are sufficiently defined to begin a test-first implementation after review. B005 must remain non-PASS until the two principal technical unknowns—real save/reopen face ownership and complete drawing-primitive attribution—are demonstrated on SolidWorks 2024 SP04. Planning completion alone is not capability validation.
