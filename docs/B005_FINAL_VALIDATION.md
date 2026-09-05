# B005 Final Validation Review

## Review status

- Repository: `solidworks-main-skill`
- Branch: `feat/benchmark-005-multi-feature`
- Reviewed implementation commit: `d523351`
- Review classification: `PASS_CANDIDATE`
- Merge-review entry condition: **SATISFIED**
- Formal B005 benchmark status: **not declared by this review**
- Main merge, tag, release, and B006 work: **not performed**

`PASS_CANDIDATE` means that the defined B005 evidence gates have passed and the branch may enter merge review. It does not mean that this document promotes B005 to a released baseline or declares unrestricted multi-feature reconstruction support.

## 1. Benchmark scope

B005 validates only this defined, disjoint multi-feature part:

```text
BaseBlock
+ Offset Through Hole
+ Offset Straight Slot
```

Canonical geometry:

- BaseBlock: 100 × 60 × 20 mm.
- Offset Through Hole: Ø20, model-centred position (-25, -10) mm, Z axis, through-all.
- Offset Straight Slot: overall length 40 mm, width 20 mm, R10 ends, model-centred position (15, 8) mm, X major axis, through-all.
- Projection contract: third angle; Front X/Y, Top X/Z, schema Left Z/Y represented by the generated SolidWorks Right view.
- Feature dependencies: `hole_001 → base_001` and `slot_001 → base_001`; Hole and Slot are independent siblings.

The hole and slot do not intersect. B005 tests coexistence, identity, evidence attribution, operation provenance, placement preservation, persisted topology ownership, and drawing roundtrip attribution. It does **not** validate complex parts, intersecting feature topology, arbitrary feature counts, freeform geometry, assemblies, sheet metal, or unrestricted drawing reconstruction.

If B005 is promoted after merge review, its `PASS` scope must remain exactly:

**BaseBlock + Offset Through Hole + Offset Straight Slot.**

It must not be presented as a general claim for complex parts.

## 2. Phase 1 result — engineering contracts

Result: **PASS for contract scope; no SolidWorks validation was claimed.**

Phase 1 introduced the backend-neutral multi-feature contracts:

- stable `feature_id`, feature type, parameters, evidence IDs, dependencies, and coordinate system;
- Base with independent Hole and Slot children;
- ModelingPlan operation ID and source-feature provenance;
- canonical Base → Hole → Slot ordering;
- `ORDER_VARIANT_EQUIVALENT` for a valid independent sibling reorder;
- ID-based multi-feature geometry validation;
- ownership strengths `API_EXACT`, `BREP_GEOMETRY_CORRELATED`, and `OWNERSHIP_UNRESOLVED`;
- outer Level 2 feature-attribution gate requiring `UNKNOWN=0` and `UNATTRIBUTED=0`.

Phase 1 deliberately did not create B005 input data or call SolidWorks COM. Its recorded final suite was 546 passed, 15 skipped, 2 deselected, and 0 failed.

## 3. Phase 2 result — structured input and evidence binding

Result: **PASS for structured input/evidence scope; B005 remained NOT VALIDATED.**

Phase 2 implemented:

```text
ProjectionGraph
→ FeatureEvidence
→ explicit primitive attribution
→ cross-view consistency
→ FeatureGraph
→ ModelingPlan provenance
```

Attribution uses stable `geometry_reference` values only. Coordinate checks validate an explicit relationship but do not create ownership by nearest-geometry search. The evidence rules require independent Front/Top/Left support for Base, Hole, and Slot and prevent either subtractive feature from borrowing the other's primitives.

Missing evidence returns `UNATTRIBUTED`; contradictory cross-view evidence returns `INPUT_INCONSISTENT`; invalid dependencies return `DEPENDENCY_VIOLATION`. Phase 2's final regression was 555 passed, 15 skipped, 2 deselected, and 0 failed.

## 4. Phase 3 result — real SolidWorks 2024 SP04

Result: **PASS_CANDIDATE for the defined B005 scope.**

Environment:

- Windows 11
- Python 3.14.5
- pytest 9.1.1
- SolidWorks 2024 SP04
- External execution backend: third-party `wzyn20051216/solidworks-automation-skill`
- Third-party source modifications: none

Executed operation plan:

1. `op_base_001` / `base_extrude`
2. `op_hole_001` / `cut_extrude_through_circle`
3. `op_slot_001` / `cut_extrude_through_slot`

The real run created the part, rebuilt it, saved it, closed it, reopened it read-only, re-read the Feature Tree and B-Rep, created the three-view drawing, saved it, and generated separate HLR and HLV semantic evidence drawings. SLDPRT, SLDDRW, JSON evidence, and four review previews exist in the local result directory. SolidWorks binary files remain ignored by the repository's existing `.gitignore`; JSON and BMP evidence is committed.

## 5. Feature Tree evidence

Initial result: **PASS**.

Reopened result: **PASS**.

Persisted feature identity is based on `IModelDocExtension.GetPersistReference3`; localized names are diagnostic only and excluded from acceptance.

| Feature ID | Feature type evidence | Profile/sketch relationship | Tree order |
| --- | --- | --- | ---: |
| `base_001` | `Extrusion` | present | 1 |
| `hole_001` | `Cut` / `ICE` | present | 2 |
| `slot_001` | `Cut` / `ICE` | present | 3 |

Expected and observed provenance order:

`base_001 → hole_001 → slot_001`

The separate negative control confirms that Base → Slot → Hole is accepted only as `ORDER_VARIANT_EQUIVALENT` when both cuts retain valid Base dependencies. An invalid dependency is rejected.

## 6. B-Rep evidence

Initial ID-partitioned B-Rep result: **PASS**.

Reopened ID-partitioned B-Rep result: **PASS**.

Validated geometry:

| Feature | Expected | Actual result |
| --- | --- | --- |
| Base | 100 × 60 × 20 mm | PASS |
| Hole | Ø20; (-25, -10); Z; through 20 mm | PASS |
| Slot | L40 × W20; R10; (15, 8); X; through 20 mm | PASS |

The values were derived from faces assigned to their exact feature owners. Aggregate geometry without ownership is insufficient for this gate.

## 7. Ownership evidence chain

### Part B-Rep

Only `API_EXACT` satisfies the ownership gate:

```text
IFace2.GetFeature
→ IModelDocExtension.GetPersistReference3
→ stable FeatureGraph feature_id
```

Reopened exact face evidence:

| Logical role | Face count | Exact owner |
| --- | ---: | --- |
| Base surfaces | 6 | `base_001` |
| Hole cylindrical wall | 1 | `hole_001` |
| Slot cylindrical end walls | 2 | `slot_001` |
| Slot planar side walls | 2 | `slot_001` |

Initial and reopened ownership both pass with unresolved count 0 and misattributed count 0. `BREP_GEOMETRY_CORRELATED` remains diagnostic and cannot pass the gate.

### Drawing primitives

Drawing-context persistent references alone collapse to component context and do not distinguish the three features. Exact projected-entity ownership therefore uses:

```text
model feature persistent reference
→ IView.GetCorresponding(feature)
→ IView.GetPolylines7 entity
→ IEdge.GetTwoAdjacentFaces2 / ISilhouetteEdge.GetFace
→ IFace2.GetFeature
→ view-context COM identity comparison
→ feature_id
```

For an edge shared by Base and exactly one subtractive feature, the single non-base operation descendant is its owner. Multiple non-base candidates remain unresolved. No feature-name mapping, nearest-geometry search, or matcher-tolerance reduction is used.

## 8. Level 1 result

Result: **PASS**

Level 1 simultaneously verifies:

- Front/Top/Left projection extents;
- exactly one expected Hole and one expected Slot;
- FeatureGraph → ModelingPlan parameter preservation;
- initial and reopened ID-partitioned B-Rep dimensions, positions, axes, and through states;
- saved three-view drawing structure.

The gate fails if either the Hole or Slot is missing or has incorrect geometry/placement; one correct feature cannot mask failure of the other.

## 9. Level 2A result

Result: **PASS**

The existing Infinite Support Line, Interval Coverage, circle, and arc matchers remain unchanged. B005 adds feature partitions outside those matchers. The following expected partitions all pass:

- Base Front/Top/Left visible outlines;
- Hole Front visible circle;
- Hole Top/Left hidden supports;
- Slot Front visible tangent lines and arcs;
- Slot Top/Left hidden supports.

A geometric primitive must match inside its expected `feature_id` partition. Geometry appearing under the wrong owner fails even when the aggregate union of drawing geometry is unchanged.

## 10. Level 2B result

Result: **PASS**

- Visible provenance: `HLR_CAPTURE`
- Hidden provenance: `HLV_MINUS_HLR`
- Feature ownership: exact view-context topology chain described above
- Required hidden supports: matched for both Hole and Slot in Top and Left schema views
- Existing semantic matcher tolerances: unchanged

## 11. UNKNOWN count

`UNKNOWN = 0`

No required projected primitive relies on unknown visibility semantics in the final attributed evidence.

## 12. UNATTRIBUTED count

`UNATTRIBUTED = 0`

Every captured B005 projected primitive in the accepted HLR/HLV evidence has an exact Base, Hole, or Slot owner. If a later run cannot reproduce this condition, Level 2 attribution must fail rather than guess.

## 13. Negative tests

All required negative controls produced their expected result:

| Negative control | Expected | Actual |
| --- | --- | --- |
| Hole ownership swapped | FAIL | FAIL |
| Slot ownership swapped | FAIL | FAIL |
| Missing Hole evidence | UNATTRIBUTED | UNATTRIBUTED |
| Missing Slot evidence | UNATTRIBUTED | UNATTRIBUTED |
| Geometry correct but owner wrong | FAIL | FAIL |
| Valid but different independent-feature order | ORDER_VARIANT_EQUIVALENT | ORDER_VARIANT_EQUIVALENT |
| Invalid dependency | DEPENDENCY_VIOLATION | DEPENDENCY_VIOLATION |

Unit coverage also rejects swapped Level 2 ownership, missing attribution, and non-zero unknown counts.

## 14. Regression result

Canonical command:

```powershell
python -m pytest -v
```

Final validation result:

- 565 passed
- 15 skipped
- 2 deselected
- 0 failed
- 26 existing ezdxf/NumPy deprecation warnings

No B001–B004 benchmark input, golden data, matcher threshold, or expected result was changed for B005 validation.

## 15. UPSTREAM_GAP and limitations

The following gap remains open and must not be closed by this review:

`UPSTREAM_GAP: SolidWorks 2024 create_semicircular_slot width semantics`

The third-party helper produces half the requested profile width under the tested SW2024 behavior. The main-project adapter retains the established minimal compatibility path; third-party source code was not modified.

Additional bounded limitations:

- exact drawing attribution requires live view-context COM identity; drawing-context persistent reference values alone are insufficient;
- the B005 contract covers one disjoint Hole and one disjoint Straight Slot only;
- intersecting cuts and topology-changing feature interactions are not validated;
- review images confirm the defined geometry visually, but they do not expand the benchmark's semantic scope.

## Merge review determination

**YES — the branch satisfies the technical and regression conditions to enter merge review.**

This determination means reviewers have complete Phase 1–3 contracts, real SolidWorks evidence, strict ownership evidence, negative controls, and a zero-failure regression baseline to review. It is not a merge action, release approval, tag, final B005 PASS declaration, or capability claim beyond the defined benchmark scope.
