# Drawing automation research

## Source-level findings

- `eyfel/mcp-server-solidworks/.../SolidWorksService.Drawing.cs` has `CreateDrawing`, `AddDrawingView`, and explicit standard-name mapping (`*Front`, `*Top`, `*Right`, `*Left`, etc.). It sets `IView.ScaleDecimal`, uses `IView.SetDisplayMode3`, and contains separate drawing/dimension/section tool paths. It is AGPL and therefore architecture/API reference only.
- `maowiz/step2pdf` uses FreeCAD Part geometry analysis, TechDraw, ISO 5455 scale selection, a first-angle three-view cluster and rule-based dimension recipes. Its README explicitly describes family classifier → dimension recipe; this maps well to a `DimensionPlanner` strategy.
- `getvenkateshprasad-sys/step-to-drawing` uses a symmetry-plane section, overall dimensions, unique diameter callouts, and a Z-axis hole table. This is a strong checklist for `SectionViewPlanner`/`DimensionPlanner`, but has no declared license.

## Planner decomposition

| Current target | Extracted design |
|---|---|
| `ViewPlanner` | choose primary view from feature salience; select first/third-angle cluster explicitly |
| `ViewLayoutPlanner` | candidate sheet/scale search, view bounding boxes, spacing constraints, collision check |
| `DimensionPlanner` | feature-family recipe; overall dimensions first, unique diameters, then datum-based locations |
| `SectionViewPlanner` | score planes by internal-feature information gain, symmetry, and annotation cost |
| `DrawingValidator` | verify views, scale, no overlap, dimension coverage, semantic annotations and exported artifact |

No repository reviewed proves a production-quality automatic section/dimension planner. Treat all drawing automation claims as constrained recipes plus QA, not universal drafting intelligence.
