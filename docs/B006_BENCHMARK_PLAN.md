# B006 Benchmark Plan — Pattern / Repeated Feature

Status: **PLANNING ONLY; B006 NOT VALIDATED**.

This document proposes a benchmark contract. It adds no implementation,
benchmark input, golden data, test code, or SolidWorks COM execution.

## 1. Baseline, environment, and scope

- Main project: `solidworks-main-skill`.
- Local baseline: `v0.5-benchmark-005`, merge `aef209a`.
- B001–B005 accepted within their defined scopes; existing data remains frozen.
- Windows 11, Python 3.14.5, pytest 9.1.1, SolidWorks 2024 SP04.
- All future tests use `python -m pytest`.
- Third-party `wzyn20051216/solidworks-automation-skill` remains an external
  execution backend. Its source must not be modified.

B006 covers one BaseBlock and one one-direction linear pattern of cylindrical
through holes. It evaluates seed identity, native pattern provenance, instance
identity, repeated geometry, and projected instance attribution.

Excluded: two-direction grids, circular patterns, variable spacing, skipped or
suppressed instances, multiple seeds, intersecting holes, body/sketch patterns,
assemblies, blind holes, and complex parts.

## 2. Proposed canonical geometry

The following placement is a design choice for this benchmark, not a measured
result. Units are mm; model X/Y coordinates are centred on the base.

- BaseBlock: 100 × 60 × 20.
- Seed: Ø10 cylindrical through hole, axis parallel to Z, centre (-35,-10).
- Linear pattern direction: signed model +X = (1,0,0).
- Centre-to-centre spacing: 20.
- Total physical hole count: 4 **including the seed**.
- Generated copies: 3; seed occurrence index 0, copy indices 1–3.
- Position rule: `p(i) = (-35,-10,0) + i × 20 × (1,0,0)`.
- Through extent: entire 20 mm base depth; the existing backend's signed
  extrusion convention must be recorded and mapped explicitly.

| Instance ID | Index | Model centre X/Y | Front view-local centre | Diameter |
| --- | ---: | --- | --- | ---: |
| `Hole_001` | 0 (seed occurrence) | (-35,-10) | (15,20) | 10 |
| `Hole_002` | 1 | (-15,-10) | (35,20) | 10 |
| `Hole_003` | 2 | (5,-10) | (55,20) | 10 |
| `Hole_004` | 3 | (25,-10) | (75,20) | 10 |

All holes are disjoint, with 10 mm material between neighbouring cylindrical
envelopes. IDs express occurrence identity; they must not be inferred from
localized SolidWorks feature names or API enumeration order.

## 3. Structured projection contract

Use standard orthographic third-angle input with the existing explicit
Front/Top/Left-to-generated-view frame mapping. Image parsing and OCR are out
of scope. A future input must contain dimensions plus an explicit pattern
declaration: seed reference, signed direction, spacing, and total count.

Front: 100 × 60 outer rectangle and four Ø10 circles at the tabled centres.
Top: 100 × 20 rectangle and eight full-depth hidden supports at X =
10, 20, 30, 40, 50, 60, 70, 80. Each adjacent pair belongs to one instance.
Left schema view: 20 × 60 rectangle and two unique full-depth hidden supports
at Y=15 and Y=25. All four holes project onto those same two supports.

Repeated projection geometry alone cannot distinguish four independently cut
holes from a native feature pattern, nor uniquely establish a seed or signed
pattern direction. Without the explicit pattern declaration, return
`AMBIGUOUS_PATTERN_INTENT`; do not choose a seed by sorting circles.
Contradictory declared spacing, positions, counts, or view extents produce
`INPUT_INCONSISTENT` before any modeling step.

## 4. FeatureGraph extension proposal

Keep existing B001–B005 typed features and semantics unchanged. Introduce
separate pattern-aware contract handling in a later implementation phase.

| Node | Proposed fields | Meaning |
| --- | --- | --- |
| `SeedFeature` | feature_id=`seed_001`, type=THROUGH_HOLE, diameter, axis, through, seed position, source_evidence_ids, dependencies=[base_001] | One actual seed cut |
| `PatternFeature` | feature_id=`pattern_001`, seed_feature_id, direction_vector, spacing_mm, total_count=4, includes_seed=true, source_evidence_ids, dependencies=[seed_001] | One native linear feature pattern |
| `InstanceFeature` | instance_id, pattern_id, seed_feature_id, index, transform_from_seed, dependencies=[pattern_001] | Semantic occurrence, not an independent cut operation |

`Hole_001` is the pattern's seed occurrence and references `seed_001`; it does
not create a second physical seed hole. All four InstanceFeature nodes belong
to the pattern. Their positions and dimensions derive from the seed and pattern
transform; independent expected values belong in the future test oracle only.

Derived occurrences must not be appended as four standalone executable Hole
nodes. Pattern-level count is four, not four copies plus one seed.

## 5. Dependencies and ModelingPlan

Creation dependencies:

```text
base_001
└── seed_001
    └── pattern_001
        ├── Hole_001 (seed occurrence)
        ├── Hole_002
        ├── Hole_003
        └── Hole_004
```

Instances must not depend directly on Base. Pattern must resolve exactly one
seed, and its seed must belong to the base. Missing references, cycles, direct
instance-to-Base edges, or execution before a parent are `DEPENDENCY_VIOLATION`.
Pattern does not depend on its derived instances, avoiding a dependency cycle.

Proposed executable plan: `base_extrude → seed cut_extrude_through_circle →
linear_feature_pattern`. Three operations yield four physical holes.
The pattern operation records the seed operation ID and its pattern parameters.
Instances inherit operation provenance through the seed/pattern relation.

The current validator requires all non-base nodes to depend directly on Base
and one operation per feature. Those B005-specific assumptions must remain
valid for B005; future B006 handling needs explicit node-role dispatch, not a
global relaxation. A loop issuing four independent cuts is insufficient to
pass the native-pattern execution gate even if final geometry matches.

## 6. Seed and instance ownership

Distinguish two identities:

- Native feature owner: which actual SolidWorks feature owns a face.
- Semantic occurrence owner: which `Hole_00N` the face realizes.

Proposed evidence fields include entity_id, persistent_entity_reference,
native_owner_feature_id, seed_feature_id, pattern_id, instance_id,
instance_index, identity_source, correspondence_source, and strength.

Seed occurrence evidence must trace the seed cut to `Hole_001`. Copies must
trace the pattern operation and its instance correspondence to `Hole_002`–004.
A face owned by the native pattern feature is not by itself evidence of which
copy it belongs to. Actual API owner semantics must be investigated after
save/reopen; the plan does not assume each copy has a separate Feature Tree node.

Only `API_EXACT` may pass the proposed strict occurrence-ownership gate.
Persistent face/feature references and explicit API instance correspondence
are candidate evidence mechanisms, subject to future SDK/documentation review
and real testing. Existing `IFace2.GetFeature` and view correspondence are
starting points, not proof that instance-level correspondence is available.

Coordinates and predicted transforms may corroborate an established identity,
but nearest geometry, index in an unordered face array, or feature-name parsing
cannot establish ownership. `BREP_GEOMETRY_CORRELATED` remains diagnostic.
If native owner is exact but occurrence identity is not, record both facts and
return `OWNERSHIP_UNRESOLVED`; B006 cannot pass by weakening that gate.

## 7. Drawing attribution and coincident projections

Every Front circle and Top hidden pair must retain a trace to its instance,
seed, and pattern. Bind expected primitives through explicit evidence references;
collect actual attribution independently through the generated drawing entities.

The Side/Left projection needs a many-to-many relation: a unique support at
Y=15 or Y=25 has contributors `{Hole_001,Hole_002,Hole_003,Hole_004}`. Store
geometric support identity separately from the complete contributor set.
Do not draw or count four coincident supports as four independently visible lines.

Geometry deduplication must preserve contribution multiplicity. Compare exact
expected and actual contributor sets for shared supports; a nonempty owner set
is not enough. Never copy the expected set to the actual side merely because
four matching Front circles exist. If the drawing API exposes only one source
for a collapsed support, investigate an exact correspondence path for the other
contributors. If unavailable, report incomplete attribution and fail that gate.

No arbitrary single instance may be chosen for a shared support. An exact set
of contributors is `SHARED_PROJECTION`, not ambiguous ownership; an unproved
set remains `UNATTRIBUTED`/`OWNERSHIP_UNRESOLVED`.

## 8. Level 1 — count, positions, dimensions

Require all of the following in a future real run:

- one base with 100 × 60 × 20 envelope;
- one seed cut and one actual native linear feature pattern;
- four distinct through-hole occurrences, including the seed once;
- Ø10 for every occurrence, correct axis and full-depth through termination;
- all four per-instance positions, 20 mm spacing, and signed +X direction;
- no missing, duplicate, suppressed, or extra occurrence;
- graph/plan parameters agree with independently read-back pattern definition
  and measured B-Rep, before and after saving, closing, and reopening;
- dependency and seed/instance provenance remain valid after reopen.

Pattern parameter readback alone cannot establish four physical holes; B-Rep
alone cannot establish native pattern intent. Both are required. Keep existing
matcher tolerances unchanged and document the reused numerical tolerances.

## 9. Level 2A — repeated geometry and attribution

Reuse existing line support/interval coverage and circle geometry comparisons.
Add occurrence-level and shared-support attribution outside the geometry matcher.

- Front: four individually attributed Ø10 circles; one-to-one occurrence coverage.
- Top: eight hidden supports forming four independently attributed pairs.
- Side/Left: two unique supports, each with all four exact instance contributors.
- Base outlines: separately attributed to Base.
- All views: reject extras as well as missing geometry and missing contributors.
- Equal circles cannot exchange instance IDs and still pass.
- Split/merged line segmentation may be equivalent only when geometry coverage
  and complete contributor sets are both preserved.

Matching the union of geometry is insufficient when occurrence attribution fails.

## 10. Level 2B — semantics

Preserve visibility evidence sources `HLR_CAPTURE` and `HLV_MINUS_HLR`.
Require `UNKNOWN=0` and `UNATTRIBUTED=0` across all required primitives and
contributors, not merely across entries the extractor happened to return.
Also require missing/extra instance and contributor counts to be zero.

Any required centre annotation must be explicitly declared in the future input
and verified separately from model edges; centre annotations cannot prove
occurrence ownership. No new annotation support is assumed by this plan.

## 11. Proposed negative tests

| Mutation | Required outcome |
| --- | --- |
| Missing Hole_003 in actual B-Rep | FAIL: missing instance |
| Count 3 or 5; seed counted twice | FAIL: count mismatch |
| Spacing 18 instead of 20 | INPUT_INCONSISTENT for input conflict; FAIL for execution mismatch |
| Direction -X or +Y instead of +X | INPUT_INCONSISTENT or FAIL, according to stage |
| Wrong seed ID, position, or diameter | dependency/input failure or seed geometry FAIL |
| Swap Hole_002/Hole_003 identities, retain geometry union | FAIL: instance attribution mismatch |
| Four independent cuts replace native pattern | FAIL: native pattern provenance missing |
| Every instance depends directly on Base | DEPENDENCY_VIOLATION |
| Cyclic or nonexistent seed reference | DEPENDENCY_VIOLATION |
| Missing explicit pattern intent | AMBIGUOUS_PATTERN_INTENT |
| Native pattern owner known, instance correspondence missing | OWNERSHIP_UNRESOLVED; no acceptance |
| Shared side support loses one contributor | FAIL / UNATTRIBUTED despite unchanged visible union |
| Extra instance contributor on a support | FAIL: contributor-set mismatch |
| UNKNOWN visibility or unattributed required entity | FAIL |
| Wrong diameter/depth on one copy after reopen | FAIL |

Positive controls: reordered API enumeration must preserve stable IDs; legitimate
support segmentation changes and sheet translation/scale changes may pass with
unchanged geometry and attribution. These are planned tests, not executed results.

## 12. Future implementation gates and unresolved capability

1. Review this geometry, node-role, dependency, and shared-support contract.
2. Implement pure schemas/validators and structured input in a later authorized phase.
3. Investigate native feature-pattern creation/readback and exact occurrence
   ownership using official SDK/API evidence before choosing adapter methods.
4. Only then execute real SolidWorks save/reopen and drawing regeneration.
5. Run B001–B005 regression with `python -m pytest -v` and the existing real
   benchmark procedures before considering any B006 acceptance.

The current B005 schema has scalar feature attribution and direct-Base dependency
assumptions; repeated occurrence identity and shared projected contributor sets
require new contracts. This plan makes no claim that SolidWorks 2024 currently
supplies the exact per-instance information needed by those contracts.

Keep open: `UPSTREAM_GAP: SolidWorks 2024 create_semicircular_slot width semantics`.
Pattern creation/readback or occurrence-correspondence gaps discovered later must
be recorded separately. A geometry-only fallback cannot be called pattern success.

Current deliverable is this document only. No B006 code, COM run, benchmark data,
test execution, baseline tag, or PASS declaration is part of this planning phase.
