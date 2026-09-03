# Three-view reconstruction experiment

Deterministic experiment only: structured standard orthographic views -> projection graph -> feature graph -> modeling plan -> SolidWorks Skill backend -> B-Rep and drawing round trip. No OCR, raster parsing, or LLM inference is used.

Run from repository root:

```powershell
py experiments\three_view_reconstruction\run_benchmark.py --case case_001_block_hole
```

The input coordinate system uses a lower-left drawing origin. Internal part coordinates are centered at the base-block centre. Projection mapping is isolated in `parser/projection_mapping.py`.
