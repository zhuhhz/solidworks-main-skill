# B005 Multi-Feature Interaction — Phase 2 Progress

Date: 2026-09-05

Branch: `feat/benchmark-005-multi-feature`

Starting commit: `1de27c8`
Status: **structured input and evidence binding implemented; SolidWorks COM not run; B005 is NOT VALIDATED**

## Scope completed

Phase 2 implements the backend-neutral path:

```text
ProjectionGraph
→ FeatureEvidence
→ explicit primitive attribution
→ cross-view consistency
→ FeatureGraph
→ ModelingPlan provenance
```

It adds the structured B005 input for a 100 × 60 × 20 mm BaseBlock with:

- one Ø20 Z-axis through hole at model-centred `(-25,-10)` / Front `(25,20)`;
- one 40 × 20, R10, X-major through slot at model-centred `(15,8)` / Front `(65,38)`;
- independent `base_001 → hole_001` and `base_001 → slot_001` dependencies.

The input contains an `expected_features` benchmark oracle. Inference does not copy this oracle into FeatureGraph. It derives the BaseBlock, Hole, and StraightSlot from explicitly referenced projection primitives, then tests the derived graph against the oracle.

## FeatureEvidence contract

Each record contains:

- `feature_id`;
- stable `evidence_id`;
- `view`: `front`, `top`, or `left`;
- `geometry_type`: `LINE`, `HIDDEN_LINE`, `HIDDEN_LINE_PAIR`, `CIRCLE`, `ARC`, or `CENTERLINE`;
- stable `geometry_reference` to a projection primitive ID;
- confidence in `[0,1]`;
- evidence `source`.

Projection primitives carry only a `primitive_id`; they do not carry a feature owner. Attribution therefore remains a separate evidence layer. Duplicate IDs, nonexistent references, declared/actual view or geometry-type mismatches, unsupported feature IDs, and a primitive assigned to more than one feature all fail explicitly.

## Attribution rules

Attribution uses `EXPLICIT_EVIDENCE_REFERENCE` only. The result records `owner_guessing_used=false`.

### BaseBlock

- exactly four referenced visible boundary lines in each view;
- the lines must form the complete Front, Top, and Left outer rectangles;
- interior slot lines cannot substitute for BaseBlock boundaries.

### Through hole

- one referenced Front circle;
- one independently referenced Top hidden-line pair plus its two full-depth hidden lines;
- one independently referenced Left hidden-line pair plus its two full-depth hidden lines;
- Front circle X must equal the Top pair midpoint;
- Front circle Y must equal the Left pair midpoint;
- pair separations must equal the Front diameter;
- hidden supports must realize the referenced pairs and span the complete depth.

This removes the old single-feature shortcut where any Top and Left pair could confirm a hole.

### Straight through slot

- two referenced Front tangent lines and two referenced semicircular arcs;
- one referenced Top overall-extent pair and four full-depth supports;
- one referenced Left width pair and two full-depth supports;
- the existing B003/B004 slot geometry contract is run on an isolated graph containing only the slot's attributed primitives.

Consequently, hole evidence cannot be borrowed by the slot, and slot evidence cannot be borrowed by the hole. Coordinates validate a declared evidence relationship; no nearest-geometry search creates ownership.

## Failure semantics

- invalid/swapped evidence schema or feature/geometry role: `FAIL / EVIDENCE_ATTRIBUTION_INVALID`;
- missing required binding or an unbound projection primitive: `UNATTRIBUTED`, with FeatureGraph status `AMBIGUOUS`;
- inconsistent Front/Top/Left geometry after explicit binding: `FAIL / INPUT_INCONSISTENT`;
- invalid FeatureGraph dependency: `FAIL / DEPENDENCY_VIOLATION`.

No ambiguous case is converted to a guessed owner.

## Generated FeatureGraph and ModelingPlan

```text
base_001: BASE_BLOCK
├── hole_001: THROUGH_HOLE  depends_on=[base_001]
└── slot_001: STRAIGHT_SLOT depends_on=[base_001]
```

The existing operation vocabulary is retained:

| Feature | Operation | Operation dependency |
| --- | --- | --- |
| `base_001` | `base_extrude` | none |
| `hole_001` | `cut_extrude_through_circle` | `op_base_001` |
| `slot_001` | `cut_extrude_through_slot` | `op_base_001` |

Every operation retains `operation_id`, `source_feature_id`, and `depends_on_operation_ids`. No new backend feature type or operation type was introduced.

## Tests

Canonical commands:

```powershell
python -m pytest tests/unit/test_b005_evidence_binding.py -v
python -m pytest -v
```

Results:

- Phase 2 evidence-binding tests: **9 passed, 0 failed**;
- B002–B005 focused contract regression: **56 passed, 0 failed** before the final two Phase 2 audit tests;
- complete suite: **555 passed, 15 skipped, 2 deselected, 0 failed**;
- existing unrelated ezdxf/NumPy deprecation warnings: 26.

The tests cover independent Hole and Slot binding, structured oracle agreement, swapped evidence, missing evidence, cross-view conflict, Base/Slot boundary swapping, independent dependencies, dependency violation, and Feature-to-Operation provenance.

## Protected boundaries

- no SolidWorks COM call was made;
- no adapter or backend implementation was changed;
- third-party `wzyn20051216/solidworks-automation-skill` source was not modified;
- B001–B004 benchmark inputs, results, reports, and golden data were not modified;
- matcher algorithms and tolerances were not modified;
- no B005 SLDPRT, SLDDRW, B-Rep evidence, or PASS claim was produced.

## Unresolved SolidWorks API questions

Phase 2 intentionally leaves the real execution gates unresolved:

1. Stability of `IFace2.GetFeature` ownership for the hole wall and all slot wall faces after save/reopen in SolidWorks 2024 SP04.
2. Availability of usable `IEdge` entities from `IView.GetPolylines7` for every B005 visible and hidden support, including silhouettes.
3. Completeness of `IEdge.GetTwoAdjacentFaces2` → face owner → feature ID attribution without nearest-reference fallback.
4. Correct handling of supports that can only be reported as `BREP_GEOMETRY_CORRELATED`; this strength cannot satisfy exact B-Rep ownership.
5. Separation and attribution of the close Left-view supports at Y=28 mm and Y=30 mm in actual HLV-minus-HLR output.
6. The existing SW2024 `create_semicircular_slot` width-semantics `UPSTREAM_GAP`, which remains open.

## Next gate

The next phase may connect the main-project SolidWorks adapter and collect operation, save/reopen, Feature Tree, B-Rep ownership, Level 1, attributed Level 2A, and attributed Level 2B evidence. Any unresolved owner must remain `OWNERSHIP_UNRESOLVED`.

**B005 remains NOT VALIDATED.**
