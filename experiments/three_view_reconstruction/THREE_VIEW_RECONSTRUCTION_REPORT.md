# Three-view → SolidWorks 3D reconstruction report

Date: 2026-09-03. Scope: deterministic Benchmarks 001/002 only. No OCR, raster/image analysis, vision model, LLM, or production-module refactor was used.

## 1. System architecture

```text
structured JSON views
  -> ProjectionGraph
  -> ProjectionConsistencyValidator
  -> FeatureHypothesis rules
  -> FeatureGraph
  -> ModelingPlan
  -> SolidWorks backend (existing Skill only)
  -> SLDPRT + B-Rep / Feature Tree evidence
  -> regenerated SLDDRW
  -> Level 1 invariant validator + Level 2 projected-primitive probe
```

The experiment code is isolated under `experiments/three_view_reconstruction/`. The parser/inference layer contains no COM calls. `backend/solidworks_backend.py` is the only adapter allowed to call the existing Skill.

## 2. Input format

The v0.1 input is structured JSON, not an image. See [case_001_block_hole.json](benchmarks/case_001_block_hole.json).

- Input units: mm.
- Drawing coordinates: lower-left origin.
- Front view: X/Y; Top view: X/Z; Left view: Z/Y.
- The sample uses third-angle projection.
- Hidden-line pairs in Top and Left are required evidence before a Front-view circle becomes a confirmed through-hole.

## 3. Projection Graph

`schemas/projection_graph.py` contains Front/Top/Left view geometry. `parser/projection_mapping.py` is the independent source of truth for:

- `front.x == top.x`
- `front.y == left.y`
- `top.z == left.z`

It also converts the external drawing origin to the model-centred coordinate system. A mismatch produces `INPUT_INCONSISTENT` and blocks the backend.

## 4. Feature Graph

`FeatureGraph` stores `BaseBlock`, `Hole`, and auditable `FeatureHypothesis` objects. The Benchmark 001 hypothesis was:

```json
{"feature_type":"through_hole","confidence":0.92,
 "evidence":["circle_in_front_view","hidden_lines_in_top_view","hidden_lines_in_left_view"]}
```

If either supporting hidden-line pair is absent, inference returns `AMBIGUOUS` with `hole_or_cylindrical_boss`; it does not call SolidWorks.

## 5. Modeling Plan

The actual plan contained two operations:

1. `base_extrude`: centred 100 × 60 mm rectangle on `Front Plane`, 40 mm depth.
2. `cut_extrude_through_circle`: Ø20 circle at internal (0,0), through all.

This plan is serializable and backend-neutral. It can later receive a FreeCAD/Fusion/Inventor backend without changing parsing or inference.

## 6. Benchmark 001

Input: 100 × 60 × 40 block with one centred Ø20 through-hole. Result: **PASS**.

- Input consistency: all three projection dimension correspondences passed at 0.01 mm tolerance.
- Feature inference: BaseBlock 100/60/40 and one confirmed `through_hole`.
- SolidWorks model: [case_001_block_hole.sldprt](results/case_001_block_hole/case_001_block_hole.sldprt).
- Feature Tree: `BaseBlock` (`Extrusion`) and `ThroughHole_D20` (`ICE`).
- B-Rep: 100.0 × 60.0 × 40.0 mm, one internal Ø20.0 cylindrical face, axial length 40.0 mm.

## 7. Benchmark 002

Implemented and actually executed: [case_002_step_block.json](benchmarks/case_002_step_block.json) → [result](results/case_002_step_block/benchmark_results.json).

- Base: 100 × 60 × 20 mm; centred boss: 60 × 40 × 20 mm; total height: 40 mm; centred Ø20 through-hole.
- Multi-view boss rule requires `visible_step_in_front`, `reduced_width_in_top`, and `height_transition_in_left`; insufficient evidence returns `AMBIGUOUS` (`boss_or_recess`).
- Actual Feature Tree: `BaseBlock`, `Plane_Base_Top`, `TopBoss`, `Plane_Boss_Top`, `ThroughHole_D20`.
- Actual B-Rep: 100 × 60 × 40 mm envelope and one internal Ø20 cylinder of 40 mm axial length. Save/reopen, drawing creation, and Level 1 invariants passed.
- The two reference planes are a minimal local compatibility supplement because the third-party backend does not expose a one-call stepped-boss operation. They are recorded as `UPSTREAM_GAP`, not claimed as an upstream capability.

## 8. Benchmark 003

Not implemented or run in this task. `inference/slot_inference.py` is intentionally a no-op placeholder; a slot has not been inferred or modeled.

## 9. SolidWorks execution result

The backend reused only existing project interfaces:

- `SolidWorksSession.new_part/save/open/new_drawing`
- `sw_part.sketch/sketch_rectangle/extrude_boss`
- `sw_hole_features.create_through_hole`
- `sw_review.collect_model_summary/collect_geometry_measurements/run_review`
- `sw_drawing.create_standard_views_with_projection/inspect_drawing_structure`

It did not add a new COM connection, drawing, or B-Rep wrapper. The regenerated drawing is [case_001_block_hole.slddrw](results/case_001_block_hole/case_001_block_hole.slddrw).

## 10. B-Rep / Bounding Box validation

`ReconstructionValidator` passed all checks:

- bounding box matches 100 × 60 × 40 mm;
- Feature Tree contains base extrusion;
- Feature Tree contains named hole cut;
- B-Rep contains the expected Ø20 internal cylinder.

The project B-Rep reader reports through state as `unknown` by design; through status is established by `create_through_hole` creation evidence plus the 40 mm cylindrical length.

## 11. 2D → 3D → 2D round-trip validation

The backend regenerated a third-angle SLDDRW with Front, Top, and Right views (the current drawing API labels the side view as `right`; the structured input calls the corresponding depth/height view `left`). The drawing structure reports three views and 1:2 scale.

The v0.1 round trip passed these structural checks:

- Front 100 × 60;
- Top 100 × 40;
- side 40 × 60;
- Ø20 at input drawing coordinate (50,30);
- regenerated drawing contains three actual SolidWorks views.

Level 1 remains PASS for both cases. Level 2 calls real SW2024 `IView.GetPolyLinesAndCurves(0)` using an `IDrawingDoc`/`IView` typed wrapper generated from the locally installed SolidWorks type library. It obtains actual projected polylines (including front-view circular-edge tessellation) in model metres. The tested API output is already independent of the 1:2 sheet scale, so the extractor converts metres to millimetres and removes only canonical bounding-box translation; it does not apply the scale a second time.

The actual response in this run does **not** expose a reliable hidden/visible line-style discriminator, nor centre-mark entities; centre marks are annotations rather than model-edge polylines. Therefore Level 2 is deliberately `PARTIAL`, never PASS: required hidden-line semantic matching cannot be truthfully evaluated. Primitive canonicalisation and tolerance matcher are present and report precision/recall/missing/extra, but benchmark input convention versus API orientation still needs calibrated mapping before visible-line scores are meaningful.

## 12. Drawing Geometry Extraction and Level 2 limitation

`drawing/drawing_geometry_extractor.py` is a temporary main-project adapter for the explicit `UPSTREAM_GAP` (no upstream projected-primitive extractor). It uses only real SolidWorks 2024 API output, not model B-Rep or raster data. The failed probes are preserved in code history: dynamic `IModelDoc2` did not expose `GetCurrentSheet`/`GetFirstView`; typed wrappers generated with `makepy` were required. `GetVisibleEntities*` was rejected for this task because it returns model topology, not drawing-space primitives.

## 13. Negative tests

Benchmark 002 executed all requested guards:

- Front width 100 / Top width 95 → `INPUT_INCONSISTENT`.
- Only a front step clue → `AMBIGUOUS` (`boss_or_recess`).
- Removed Top hole hidden-line evidence → `AMBIGUOUS`.

## 14. Currently supported features

- Structured standard orthographic dimensions.
- Rectangular base block.
- One or more Front-view circles only when two orthogonal hidden-line evidence sets confirm a Z-axis through-hole.
- Base extrusion and through circular cut.
- Input consistency blocking, model reopening, Feature Tree/B-Rep validation, and structural drawing regeneration.

## 15. Currently unsupported features

- SVG/DXF and PNG/JPG input parsing.
- OCR, image segmentation, line type classification, scale recovery.
- Blind holes, slots, symmetry inference, revolve inference; only the constrained centred boss rule is implemented.
- Full first-angle positioning semantics in the round-trip comparator.
- Reliable hidden/centre-line semantic extraction and calibrated orientation mapping for direct linework comparison.
- Pixel-level comparison, dimension placement, complete drawing quality gate.

## 16. Ambiguity handling

The system does not guess. A front circle alone is ambiguous between a hole and a cylindrical boss/recess. Missing orthogonal hidden-line evidence results in:

```json
{"status":"AMBIGUOUS","candidates":["hole_or_cylindrical_boss"],
 "reason":"insufficient evidence from top and left views"}
```

An inconsistent set of three extents results in `FAIL` / `INPUT_INCONSISTENT` before any SolidWorks document is created.

Both guards were executed: removing Top hidden-line evidence produced `AMBIGUOUS`; changing Top width from 100 to 99 mm produced `INPUT_INCONSISTENT`.

## 17. Reusable third-party solidworks-automation-skill capabilities

- Native document/session management and reopening.
- Sketch rectangle/circle, base extrusion, through cut.
- SLDPRT save and Feature Tree enumeration.
- B-Rep envelope/internal cylinder measurement.
- Native standard three-view creation and drawing structure inspection.
- Review previews and structured review reports.

## 18. Capabilities that must be developed in solidworks-main-skill

- Vector/image source parsing into `ProjectionGraph`.
- Projection correspondence matching beyond dimensions.
- Feature candidate ranking for holes/bosses/blind holes/steps/slots.
- FeatureGraph-to-plan rules for additional feature types.
- Generated drawing view line/arc/hidden-line extraction.
- Actual input-vs-generated geometric correspondence and visual/dimension comparison.
- Layout-aware drawing regeneration, because the existing drawing subsystem remains `pilot`.

## Final decision

**B. Benchmark 002 reconstruction is feasible, but Drawing Geometry Extraction has a critical semantic gap.** Both Benchmarks reconstruct actual SLDPRT/SLDDRW and pass B-Rep plus Level 1 validation. The Level 2 API probe is real and reusable, but it cannot yet distinguish hidden lines or centre lines, and its orientation mapping is not calibrated. Consequently neither benchmark is reported as a vector-geometry closed-loop PASS.
