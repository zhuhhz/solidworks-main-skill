# HLV / HLR semantic experiment

This experiment toggles the same copied SolidWorks drawing between Hidden
Lines Removed (`swHIDDEN=2`) and Hidden Lines Visible
(`swHIDDEN_GREYED=1`). It extracts projected geometry before save and after
reopen, canonicalizes line supports, and computes `HLV - HLR` candidates.

It does not modify the source benchmark drawing. A `HIDDEN` label is emitted
only with `source=HLV_MINUS_HLR`; unresolved geometry remains `UNKNOWN`.

```powershell
python experiments/hlv_hlr_semantics/run_experiment.py --case case_001_block_hole
python experiments/hlv_hlr_semantics/run_experiment.py --case case_002_step_block
```

API evidence: the installed SW2024 type library exposes
`SetDisplayMode3(UseParent, Mode, Facetted, Edges) -> bool`; official
`swDisplayMode_e` assigns HLV=1 and HLR=2.
