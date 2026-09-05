# B005 Multi-Feature Interaction — Phase 1 Progress

Date: 2026-09-05  
Branch: `feat/benchmark-005-multi-feature`  
Baseline: `v0.4-benchmark-004` / `9167a05`  
Status: **engineering contract implemented; real SolidWorks not run; B005 is not validated**

## Scope completed

This phase implements only the backend-neutral contract required before any B005 COM execution:

- normalized FeatureGraph nodes with stable `feature_id`, `feature_type`, parameters, evidence IDs, dependencies, and coordinate system;
- dependency-DAG validation for a BaseBlock with independent Hole and Slot children;
- operation ID, source-feature provenance, and operation dependency fields;
- deterministic canonical Base → Hole → Slot plan production;
- `ORDER_VARIANT_EQUIVALENT` classification for a declared valid sibling reorder;
- ID-based multi-feature geometry validation;
- explicit ownership evidence strengths;
- outer feature-attribution validation without changing existing geometry matchers;
- `UNKNOWN=0` and `UNATTRIBUTED=0` acceptance contract;
- negative coverage for wrong dimensions/placement, missing features, invalid dependencies, swapped ownership, and unresolved ownership.

No B005 benchmark JSON, COM call, adapter behavior, generated SLDPRT/SLDDRW, reference, golden data, matcher, or tolerance was added or changed.

## FeatureGraph design

Existing typed `BaseBlock`, `Hole`, `Boss`, and `StraightSlot` classes remain in place for B001–B004 compatibility. Each can now produce a normalized `FeatureNode` rather than being replaced by a large schema refactor.

The B005 in-memory graph contract is:

```text
base_001: BASE_BLOCK
├── hole_001: THROUGH_HOLE
└── slot_001: STRAIGHT_SLOT
```

Each normalized node contains:

- `feature_id`;
- `feature_type`;
- `parameters`;
- `source_evidence_ids`;
- `dependencies`;
- `coordinate_system=MODEL_CENTERED_XY_MM`.

`validate_feature_graph()` rejects missing/duplicate IDs, missing or indirect B005 cut dependencies, missing evidence, cross-feature evidence reuse, and invalid roots. It returns a deterministic topological order and explicit dependency edges.

## ModelingPlan provenance

`ModelingOperation` now has additive fields:

- `operation_id`;
- `source_feature_id`;
- `depends_on_operation_ids`.

The production `build_plan()` populates them directly from FeatureGraph metadata. `validate_modeling_plan()` verifies one operation per feature, expected feature-type/operation-type mapping, dependency equivalence, and execution order without using localized SolidWorks feature names.

For independent disjoint Hole and Slot siblings:

- Base → Hole → Slot: `CANONICAL_ORDER`;
- declared Base → Slot → Hole with valid dependencies: `ORDER_VARIANT_EQUIVALENT`;
- an operation before its required parent: `DEPENDENCY_VIOLATION`.

## Ownership evidence model

`OwnershipEvidence` records:

- `entity_id` and entity kind;
- stable `feature_id` or no claimed owner;
- evidence source;
- strength: `API_EXACT`, `BREP_GEOMETRY_CORRELATED`, or `OWNERSHIP_UNRESOLVED`;
- optional details.

An unresolved row is structurally forbidden from claiming a feature ID. Resolved rows require one. `validate_ownership_evidence()` rejects missing, extra, unresolved, or swapped owners. Feature names are not inputs to the ownership decision.

`validate_feature_attribution()` is deliberately outside the existing Level 2A primitive matchers. It combines an existing geometry result with expected/actual feature IDs and fails when geometry is correct but attribution is swapped. It also enforces both unknown and unattributed counts at zero.

## Tests

Canonical command:

```powershell
python -m pytest -v
```

Results:

- implementation baseline: 531 passed, 15 skipped, 2 deselected, 0 failed;
- B005 contract: 14 passed;
- B003–B005 focused regression: 45 passed;
- all unit tests: 68 passed;
- final complete suite: **545 passed, 15 skipped, 2 deselected, 0 failed**, 26 warnings, 18.89 seconds.

The warnings are the existing ezdxf/NumPy deprecation warnings and are unrelated to B005.

## Unresolved SolidWorks API questions

These are intentionally not answered by unit-test fixtures:

1. Whether `IFace2.GetFeature` remains stable for the hole cylindrical wall and all four slot wall faces after save/reopen in SolidWorks 2024 SP04.
2. Whether `IView.GetPolylines7` returns usable `IEdge` correspondence for every B005 hidden support, especially silhouette-derived slot end supports.
3. Whether `IEdge.GetTwoAdjacentFaces2` plus face ownership can attribute every hidden support without geometry-only guessing.
4. Which supports must be reported as `BREP_GEOMETRY_CORRELATED` when SolidWorks supplies no exact drawing-edge entity.
5. Whether the close Side-view hole/slot supports at Y=28 and Y=30 remain separately attributable in actual HLV-minus-HLR output.

If any required owner cannot be proven, the later real run must emit `OWNERSHIP_UNRESOLVED`; it must not infer ownership from `ThroughHole_D20`, `ThroughSlot_L40_W20`, list order, or nearest reference geometry.

## Boundary and next gate

The third-party `wzyn20051216/solidworks-automation-skill` remains an external execution backend and was not modified. The known SW2024 slot-width `UPSTREAM_GAP` remains open.

Phase 1 is complete. The next phase may add the structured B005 input and correspondence-specific inference only after review. Real adapter execution is allowed only after those unit tests pass. B005 must not be reported PASS until real SolidWorks save/reopen, Feature Tree, B-Rep ownership, Level 1, attributed Level 2A, attributed Level 2B, `UNKNOWN=0`, and `UNATTRIBUTED=0` all succeed.
