# B005 Phase 3 Progress — Real SolidWorks Adapter and B-Rep Ownership

## Status

`PASS_CANDIDATE` — not a released or final B005 `PASS`.

Phase 3 has completed the defined real-SolidWorks execution and validation scope. A later acceptance phase must decide whether to promote the candidate; this report does not do so.

## Environment

- OS: Windows 11
- Python: 3.14.5
- pytest: 9.1.1
- SolidWorks: 2024 SP04
- Test entry point: `python -m pytest`
- Branch: `feat/benchmark-005-multi-feature`
- External execution backend: third-party `wzyn20051216/solidworks-automation-skill`
- Third-party source changes: none

## Modeling plan and SolidWorks generation

The structured B005 input generated this provenance-bearing operation sequence:

1. `op_base_001` / `base_extrude` — 100 × 60 × 20 mm
2. `op_hole_001` / `cut_extrude_through_circle` — Ø20, center (-25, -10) mm, through
3. `op_slot_001` / `cut_extrude_through_slot` — 40 × 20 mm, R10, center (15, 8) mm, X major axis, through

Both cut operations depend directly on `op_base_001`. Parameters originate from the FeatureGraph/ModelingPlan; the adapter contains no B005 geometry constants.

## Save, close, and reopen

Real SolidWorks created and saved:

- `case_005_multi_feature.SLDPRT`
- `case_005_multi_feature.SLDDRW`

The part was closed and reopened read-only before the second Feature Tree, ownership, and B-Rep checks. Both pre-save and reopened checks are retained in `benchmark_results.json`.

## Feature Tree

Result: `PASS`

The identity path is `IModelDocExtension.GetPersistReference3`; localized feature names are diagnostic only and are excluded from acceptance.

Observed provenance order:

`base_001 → hole_001 → slot_001`

The operation type and associated profile/sketch relationship were checked for each feature. The negative control also confirms that a valid independent cut reordering is classified `ORDER_VARIANT_EQUIVALENT`, while an invalid dependency is rejected as `DEPENDENCY_VIOLATION`.

## B-Rep ownership evidence

Result before close: `PASS`.

Result after reopen: `PASS`.

Only `API_EXACT` evidence passes the ownership gate. The proof chain is:

`IFace2.GetFeature → IModelDocExtension.GetPersistReference3 → feature_id`

Reopened face-role totals:

| Role | Exact face count | Owner |
| --- | ---: | --- |
| Base surfaces | 6 | `base_001` |
| Hole cylindrical wall | 1 | `hole_001` |
| Slot cylindrical end walls | 2 | `slot_001` |
| Slot planar side walls | 2 | `slot_001` |

`OWNERSHIP_UNRESOLVED = 0`; misattributed faces = 0.

An initial real run failed while reading the dynamic `ModelDoc2.Extension` COM property (`-2147352573`, member not found). The compatibility accessor was corrected locally. A second run then exposed that `FaceInSurfaceSense=True` is an orientation flag, not proof that a planar face belongs to a cut. The classifier now distinguishes base caps and slot walls by plane normal relative to the extrusion axis; the owner itself is still proven only by the API identity chain.

## B-Rep geometry

The ID-partitioned B-Rep comparison passed before close and after reopen:

- Base bounding dimensions: 100 × 60 × 20 mm
- Hole: Ø20, center (-25, -10) mm, Z axis, through 20 mm
- Slot: overall length 40 mm, width 20 mm, R10, center (15, 8) mm, X axis, through 20 mm

Geometry correlated without exact ownership is diagnostic only and cannot satisfy this gate.

## Drawing and projected-entity attribution

The adapter generated the three standard drawing views and produced saved HLR and HLV evidence drawings. Projected geometry is read with `IView.GetPolylines7`.

Direct persistent references obtained in drawing component context collapse to that context and cannot distinguish the three features. The exact working path is instead:

1. Resolve each model feature from its model persistent reference.
2. Obtain the corresponding per-view feature object using `IView.GetCorresponding`.
3. Read each projected edge/silhouette entity returned alongside `GetPolylines7`.
4. Traverse `IEdge.GetTwoAdjacentFaces2` or `ISilhouetteEdge.GetFace`.
5. Compare `IFace2.GetFeature` COM identity with the corresponding per-view feature objects.
6. For an edge shared by the base and one cut, select the single non-base operation descendant. Multiple non-base candidates remain unresolved.

No feature name, closest point, nearest geometry, or matcher tolerance change is used.

API references:

- [IFace2.GetFeature](https://help.solidworks.com/2024/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IFace2~GetFeature.html)
- [IView.GetPolylines7](https://help.solidworks.com/2024/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.iview~getpolylines7.html)
- [Drawing views and model entities](https://help.solidworks.com/2024/english/api/sldworksapiprogguide/Overview/Drawing_Views_and_Model_Entities.htm)
- [Persistent reference IDs](https://help.solidworks.com/2024/English/api/sldworksapiprogguide/overview/Persistent_Reference_IDs.htm)

## Roundtrip results

| Gate | Result |
| --- | --- |
| Backend | PASS |
| Save/reopen | PASS |
| Feature Tree | PASS |
| B-Rep ownership | PASS |
| Level 1 multi-feature parameters | PASS |
| Level 2A vector geometry + feature attribution | PASS |
| Level 2B HLR/HLV semantics + feature attribution | PASS |
| `UNKNOWN` | 0 |
| `UNATTRIBUTED` | 0 |

All ten expected feature/view/primitive partitions pass: base visible outlines in Front/Top/Left; hole front circle and Top/Left hidden lines; slot front lines/arcs and Top/Left hidden lines.

## Negative controls

| Control | Expected/actual |
| --- | --- |
| Hole owner swapped | FAIL / FAIL |
| Slot owner swapped | FAIL / FAIL |
| Missing hole evidence | UNATTRIBUTED / UNATTRIBUTED |
| Missing slot evidence | UNATTRIBUTED / UNATTRIBUTED |
| Geometry correct, owner wrong | FAIL / FAIL |
| Valid different feature order | ORDER_VARIANT_EQUIVALENT / ORDER_VARIANT_EQUIVALENT |
| Invalid dependency | DEPENDENCY_VIOLATION / DEPENDENCY_VIOLATION |

## Test result

Command: `python -m pytest -v`

- 565 passed
- 15 skipped
- 2 deselected
- 0 failed
- 26 warnings (existing ezdxf/NumPy deprecation warnings)

## Evidence

- `experiments/three_view_reconstruction/results/case_005_multi_feature/benchmark_results.json`
- `experiments/three_view_reconstruction/results/case_005_multi_feature/attributed_roundtrip.json`
- `experiments/three_view_reconstruction/results/case_005_multi_feature/case_005_multi_feature.SLDPRT`
- `experiments/three_view_reconstruction/results/case_005_multi_feature/case_005_multi_feature.SLDDRW`
- `experiments/three_view_reconstruction/results/case_005_multi_feature/review/*.bmp`
- `experiments/hlv_hlr_semantics/results/case_005_multi_feature/*`

The generated isometric and front previews were manually inspected: the plate, offset circular through-hole, and offset straight through-slot are visibly present and non-overlapping. The automated review score is 100, but the evidence remains subject to human review as required by the SolidWorks automation skill.

## Remaining API/product limits

- `UPSTREAM_GAP` remains open: the third-party backend's semicircular-slot width semantics on SolidWorks 2024 produce half the requested profile width; the existing local compatibility path remains required. The third-party source was not modified.
- Drawing-context persistent references alone are not feature-distinguishing; exact drawing attribution depends on live view-context COM identity and must be collected in the same session.
- This result is validated only for the defined B005 geometry and view contract. It is not evidence for arbitrary multi-feature drawings.
- No release, baseline tag, or benchmark promotion is performed in Phase 3.

## Reproduction

```powershell
python -m pytest -v
python experiments/three_view_reconstruction/run_benchmark.py --case case_005_multi_feature
```

Final Phase 3 classification: `PASS_CANDIDATE`.
