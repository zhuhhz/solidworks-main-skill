# Migration plan

## Phase 1 — Level 2A/2B gate before Benchmark 003

1. Keep the official project identifier `solidworks-main-skill` in project metadata and documentation.
2. Add `CanonicalViewOrientation` and explicit Front/Top/Left ↔ generated Front/Top/Right transform tests.
3. Run a minimal controlled SolidWorks experiment: same part, HLR and HLV views created with documented `IView.SetDisplayMode3`; compare normalized projected primitives and record whether set difference isolates hidden candidates.
4. Read existing centre-mark annotations into a separate semantic channel.
5. Only declare Level 2A PASS after calibrated visible outline/circle matching; declare Level 2B PASS only after hidden/centre provenance is demonstrated.

## Phase 2 — Benchmark 003 slot

Add rectangular-slot hypotheses, `CUT_EXTRUDE` plan lowering, B-Rep verification and the same Level 2 regression gate.

## Phase 3 — stepped shaft and flange

Add revolve/cylinder hypotheses, reference axes and circular correspondence rules. Keep alternative hypotheses explicit.

## Phase 4 — vector/image ingestion

DXF/SVG parser first, mapping layers/linetypes into `SemanticPrimitiveGraph`; only then consider raster/OCR/VLM front ends.

## Phase 5 — 3D deliverable drawing

Implement planner decomposition, then bounded section/dimension recipes and PDF/DXF evidence QA.

### Priority order

1. HLV/HLR differential + canonical orientation.
2. Model-topology corroboration.
3. Timeout-bounded DXF sidecar feasibility test.
4. OpenCascade/B-Rep HLR only if prior routes fail.
