# Reference-project capability matrix

Research date: 2026-09-03. “Verified” means a repository source file or GitHub API tree was inspected; documentation alone is not proof.

| Project | 2D→3D | 3D→2D | Hidden semantics | CAD sequence | Roundtrip | Layout / dimensions / section | License | Relevance |
|---|---|---|---|---|---|---|---|---|
| third-party `wzyn20051216/solidworks-automation-skill` | execution only | SolidWorks drawing | no verified projected-line semantic reader | wrapper calls | Level 1 only here | views/dims/annotations, pilot | MIT | ★★★★ |
| `zarcherlot/q3ds-solidworks-mcp` | unknown | unknown | `DOCUMENTED_BUT_NOT_VERIFIED` | unknown | unknown | unknown | unavailable | ★ |
| `eyfel/mcp-server-solidworks` | DXF planner | SolidWorks C# tools | DXF class field, not verified SW extraction | FeatureGraph + draw dialect | not found | views/dims/section tools | AGPL-3.0 | ★★★★★ design-only |
| `elrinor/qrec` | DXF→CSG | display only | DXF linetype/color → NORMAL/PHANTOM/CENTER/CUTTING | CSG extrusion | no | sectional reasoning | no LICENSE | ★★★★★ algorithm-only |
| `lllssc/Drawing2CAD` | vector SVG→CAD tokens | synthetic SVG export | no semantic API | CAD vector sequence | model evaluation, not closed loop | n/a | MIT | ★★★★ schema/data |
| `manycore-research/PlankAssembly` | 3 SVG views→shape program | PythonOCC SVG renderer | training input variants include hidden / visible | learned shape program | render/evaluate, not engineering QA | n/a | AGPL-3.0 | ★★★ schema-only |
| `KeNiu042/CReFT-CAD` / TriView2CAD | benchmark/reasoning | DXF/PNG/STEP/B-Rep data | DXF semantic layers claimed; code release incomplete | executable script modality | benchmark tasks | n/a | no LICENSE | ★★★★ benchmark-only |
| `maowiz/step2pdf` | no | STEP→TechDraw/PDF | not relevant | rule recipes | no | scale/first-angle/dims | no LICENSE | ★★★ drawing planner |
| `getvenkateshprasad-sys/step-to-drawing` | no | STEP→TechDraw/PDF | not relevant | recipe/script | no | symmetry section/hole table | no LICENSE | ★★★ drawing planner |
| `Mohil-Ahuja/2D-to-3D-CAD-Reconstruction` | learned multi-view→Build123d | exports STEP | not verified | predicted operation tokens | dimensional validation claimed | n/a | MIT | ★★ future only |

The only inspected implementation that explicitly classifies line semantics is QRec, and it receives them from DXF linetype/color rather than from a SolidWorks drawing view.
