# Multi-view reconstruction and orientation research

## Evidence from inspected projects

- **QRec** is the closest deterministic reference. `src/qr/RelationConstructor.cpp` builds cross-view parallel/perpendicular size relations from view bounding boxes and adds name relations to sectional views. It also links a circular arc in one view to a centreline in another. `src/qr/LoopExtruder.cpp` turns a 2D loop into a CSG polyhedron along the view's perpendicular axis. It handles ambiguity conservatively through competing relations rather than treating a single view as proof.
- **Drawing2CAD** packages four separately normalized SVG views (`Front`, `Top`, `Right`, `FrontTopRight`) and paired CAD token sequences. It is useful evidence that per-view vector normalization and a serializable operation target are appropriate; its transformer correspondence is not suitable as a deterministic inference rule.
- **PlankAssembly** generates SVG orthographic views with PythonOCC and supports “complete lines”, “visible only”, and sideface input variants. Its AGPL code is reference-only, but these input modes validate keeping visibility evidence as an independent field rather than erasing it during parsing.
- **TriView2CAD** publishes six aligned modalities—parameter JSON, DXF, PNG, executable CAD scripts, STEP and B-Rep—and constraint-guided inter-view dimensional consistency. Treat it as a future benchmark-generation format, not a runtime dependency.

## Required canonical orientation model

Do not match strings such as `Right` and `Left`. Add an immutable `CanonicalViewOrientation` to every parsed or regenerated view:

```json
{"face":"FRONT","screen_u_world":"+X","screen_v_world":"+Y",
 "view_normal_world":"+Z","handedness":"RIGHT_HANDED",
 "mirrored":false,"rotation_deg":0,"projection":"THIRD_ANGLE"}
```

`ViewOrientationTransform` derives this record from a known model view and declared first/third-angle standard; it is then used to map local points, normals and dimensions. A generated `RIGHT` view may only be compared with a requested `LEFT` view after an explicit normal/handedness transform proves equivalence.

## ProjectionGraph v0.2 recommendation

Retain v0.1 fields for Benchmarks 001/002. Add, rather than replace:

- `ViewFrame` (canonical orientation plus local origin/scale/unit transform);
- `SemanticPrimitiveGraph` (lines, arcs, circles, annotations; `VISIBLE|HIDDEN|CENTER|SECTION|UNKNOWN`; source and confidence);
- `Correspondence` edges (`shared_axis`, `projected_feature`, `dimension_equal`, `centre_on_axis`) with evidence list and confidence;
- `HypothesisSet` with mutually exclusive candidates and an explicit `AMBIGUOUS` terminal state.

This matches QRec's relation/evidence approach while preserving the current backend-neutral ProjectionGraph → FeatureGraph boundary.
