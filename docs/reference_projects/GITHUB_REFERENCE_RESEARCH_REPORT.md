# GitHub reference research report

## Answers

1. **Closest overall:** QRec for deterministic multi-view evidence/CSG, and the third-party SolidWorks backend for execution. They must remain separate references.
2. **Best three-view reference:** QRec for rules; PlankAssembly/Drawing2CAD for data representations only.
3. **Best SolidWorks drawing API reference:** eyfel's C# `SolidWorksService.Drawing.cs`, but AGPL means no source reuse.
4. **Hidden semantics:** QRec genuinely classifies DXF linetype/color. No inspected project proves a direct SolidWorks projected-edge classifier.
5. **Centre semantics:** QRec has DXF dash-dot centre lines; SolidWorks centre marks should use annotations.
6. **Multi-view correspondence:** QRec uses geometric size/name/centre relations; learned projects use joint encoded views.
7. **CAD sequence:** Drawing2CAD is the clearest vector-CAD sequence reference; adopt only the backend-neutral schema principle.
8. **True 2D→3D→2D engineering QA:** none verified.
9–11. **Planner ideas:** first/third-angle clusters, scale search, recipe-based dimensions, symmetry/information-gain section planes, and hole tables.
12–13. **Lawful reuse:** MIT repositories may be reused with notice; AGPL is reference-only here; unlicensed projects are unknown/reference-only.
14. **Level 2 route:** HLV/HLR differential + topology correspondence + canonical orientation, DXF sidecar as fallback.
15. **Before Benchmark 003:** pass an orientation-calibrated Level 2A and demonstrate/deny HLV/HLR hidden semantics with a real controlled artifact.

## Ranked priorities

1. **QRec design** — directly supplies semantic primitive, evidence and ambiguity concepts.
2. **eyfel API strategy** — identifies concrete `SetDisplayMode3` leverage for the present gap.
3. **Drawing2CAD/TriView2CAD** — strongest future benchmark and operation/data schema references.
4. **step2pdf/step-to-drawing** — drawing-planner recipes after reconstruction QA is solid.

## Recommended technical direction

Adopt **SolidWorks API + canonical view orientation + semantic primitive graph + HLV/HLR differential + model-topology corroboration**. This is a hybrid route: it preserves native drawing evidence while refusing to silently invent hidden/centre labels. It is the most direct route to Level 2A/2B without adding an LLM.
