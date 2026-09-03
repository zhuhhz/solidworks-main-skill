# Hidden-line and centre-semantic research

## Source-confirmed mechanisms

### QRec: DXF semantics, not projection inference

`elrinor/qrec/src/qr/DxfReader.cpp::DxfCreationInterface::penStyle()` maps DXF `DASHDOT` to `Qt::DashDotLine`, `DASHED*` to `Qt::DashLine`, and `CONTINUOUS`/`ByLayer` to `Qt::SolidLine`. `src/qr/EdgeClassifier.cpp::operator()` then maps DashDot→`CENTER`, Dash→`PHANTOM`, blue solid→`CUTTING`, other solid→`NORMAL`. `src/qr/RelationConstructor.cpp::operator()` uses an arc centre lying on an `Edge::CENTER` line as cross-view centre evidence. This is directly relevant as a *schema and DXF-import strategy*, but cannot label the opaque polylines returned by `IView.GetPolyLinesAndCurves`.

### eyfel/mcp-server-solidworks: view display mode is explicit

`execution/solidworks/SolidworksExecution/Services/SolidWorksService.Drawing.cs::AddDrawingView()` calls `IDrawingDoc.CreateDrawViewFromModelView3`, then `IView.SetDisplayMode3(false, mode, false, false)`. Source comments map `hlv` to mode 1 and `hlr` to mode 2, with orthographic default HLV. This establishes an immediate controlled experiment: regenerate the same view once HLV and once HLR, extract polylines from both, and compute their set difference. It does **not** itself prove that `analyze_drawing(include_geometry)` maps an individual primitive to hidden/visible.

### Current third-party backend

Its drawing inspector reads view boxes and annotations; no source-confirmed drawing-space line/curve semantic reader was found. `IView.GetVisibleEntities*` is model topology, not drawing projected geometry. This remains `UPSTREAM_GAP`.

## Centre marks and centre lines

Centre marks are drawing annotations, not necessarily model-edge polylines. Keep a separate `AnnotationPrimitive` channel (`CENTER_MARK`, `CENTER_LINE`, `HOLE_CALLOUT`) and never force it into `ProjectedEdge`. QRec's centre semantic is a DXF dash-dot *edge* convention; SolidWorks centre marks must be read from annotation APIs such as the existing backend inspector's centre-mark traversal.

## Recommended Level 2 route

1. **First choice — Hybrid:** create matched HLV/HLR SolidWorks views, use canonical orientation and set-difference to propose hidden candidates, then corroborate against `GetVisibleEntities2` model topology. Persist provenance and mark unresolved primitives `UNKNOWN`.
2. **Second choice — DXF validation sidecar:** export a dedicated drawing only after a timeout-bounded reliability experiment; parse entity/layer/linetype into `SemanticPrimitiveGraph`. Earlier DXF export hangs mean this is not yet a production validator.
3. **Fallback — own B-Rep HLR:** project model edges with a view matrix and perform occlusion/depth tests. It is deterministic but substantially more work; use OpenCascade HLR only after the API/DXF experiments fail.

No examined project supplies a drop-in solution for SolidWorks projected-polyline semantic classification.
