# Three-view → SolidWorks 3D reconstruction report

Date: 2026-09-03. Scope: deterministic Benchmark 001 only. No OCR, raster/image analysis, vision model, LLM, or new production `scripts/` module was used.

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
  -> structured round-trip validator
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

Not implemented or run in this task. The requested stepped-block benchmark requires a second profile/feature inference rule and a second `base_extrude`/boss operation. It must not be claimed from Benchmark 001 evidence.

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

This is **not** linework, hidden-line, dimension, or pixel equivalence. Existing project drawing inspection returns view boxes and annotations, not a complete normalized view-geometry graph. That is the next critical implementation gap.

## 12. Currently supported features

- Structured standard orthographic dimensions.
- Rectangular base block.
- One or more Front-view circles only when two orthogonal hidden-line evidence sets confirm a Z-axis through-hole.
- Base extrusion and through circular cut.
- Input consistency blocking, model reopening, Feature Tree/B-Rep validation, and structural drawing regeneration.

## 13. Currently unsupported features

- SVG/DXF and PNG/JPG input parsing.
- OCR, image segmentation, line type classification, scale recovery.
- Blind holes, bosses, steps, slots, symmetry inference, revolve inference.
- Full first-angle positioning semantics in the round-trip comparator.
- Extracting generated SLDDRW visible/hidden geometry for direct linework comparison.
- Pixel-level comparison, dimension placement, complete drawing quality gate.

## 14. Ambiguity handling

The system does not guess. A front circle alone is ambiguous between a hole and a cylindrical boss/recess. Missing orthogonal hidden-line evidence results in:

```json
{"status":"AMBIGUOUS","candidates":["hole_or_cylindrical_boss"],
 "reason":"insufficient evidence from top and left views"}
```

An inconsistent set of three extents results in `FAIL` / `INPUT_INCONSISTENT` before any SolidWorks document is created.

Both guards were executed: removing Top hidden-line evidence produced `AMBIGUOUS`; changing Top width from 100 to 99 mm produced `INPUT_INCONSISTENT`.

## 15. Reusable solidworks-automation-skill capabilities

- Native document/session management and reopening.
- Sketch rectangle/circle, base extrusion, through cut.
- SLDPRT save and Feature Tree enumeration.
- B-Rep envelope/internal cylinder measurement.
- Native standard three-view creation and drawing structure inspection.
- Review previews and structured review reports.

## 16. Capabilities that must be developed here

- Vector/image source parsing into `ProjectionGraph`.
- Projection correspondence matching beyond dimensions.
- Feature candidate ranking for holes/bosses/blind holes/steps/slots.
- FeatureGraph-to-plan rules for additional feature types.
- Generated drawing view line/arc/hidden-line extraction.
- Actual input-vs-generated geometric correspondence and visual/dimension comparison.
- Layout-aware drawing regeneration, because the existing drawing subsystem remains `pilot`.

## Final decision

**A. Simple three-view reconstruction chain is feasible.** Benchmark 001 ran through the full structured-input → inferred-feature → SolidWorks → SLDPRT → regenerated-drawing path and passed B-Rep plus structural projection checks.

This does not establish general drawing reconstruction. The next gate is Benchmark 002, then Benchmark 003, followed by generated-SLDDRW geometry extraction before claiming a true drawing-geometry closed loop.
