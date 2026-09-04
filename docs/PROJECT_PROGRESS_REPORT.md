# solidworks-main-skill progress report

## Identity and boundary

`solidworks-main-skill` owns engineering reasoning and validation. The
third-party `wzyn20051216/solidworks-automation-skill` remains an external
SolidWorks execution backend, not this project.

## Canonical View Frame

`CanonicalViewFrame` records numeric `normal`, `up`, `right`, projection type,
mirror state, rotation, source name, and canonical role. It enforces
`right = up × normal`. English and Chinese SolidWorks names normalize to the
same frame. Sheet translation and scales 1:1, 1:2, and 2:1 do not change
view-local model geometry.

Level 2A selects regenerated views by canonical role rather than localized
view name or sheet order. Projection-graph axes are mapped through world-space
bases: Front X/Y, Top X/Z, and Left Z/Y. For the current third-angle backend,
input Left is explicitly compared with the generated Right frame.

## Support Geometry Matcher

Lines use normalized direction plus normal-form infinite support, followed by
1D interval union. The report includes support IoU, missing length, overflow
length, missing/overflow ratios, and maximum internal gap. Central thresholds
are support IoU ≥ 0.98, maximum gap ≤ 0.10 mm, overflow ratio ≤ 0.02, angle
tolerance 0.10°, and support-line distance tolerance 0.10 mm.

Equal support with different splitting returns `GEOMETRY_EQUIVALENT` and
`SEGMENTATION_DIFFERENT`. A real gap or excessive overflow fails. Circles
retain centre/radius matching and are not reduced to line supports after the
extractor has recognized their tessellation.

## B002 Level 2A Result

B002 remains `PARTIAL`, supported by actual SolidWorks evidence. After
canonical Top and Right/Left axis mapping, Front IoU is 1.0, Top IoU is
0.823529 with 60 mm overflow, and Right IoU is 0.833333 with 40 mm overflow.
Missing length is zero in both side views. The excess is a real continuous
visible feature edge in the regenerated views, not a segment split/merge, so
thresholds and expected data were not relaxed.

## HLV / HLR Experiment

The independent `experiments/hlv_hlr_semantics` probe uses the installed
SW2024 signature `IView.SetDisplayMode3(False, mode, False, False)`. Official
`swDisplayMode_e` values HLV=1 and HLR=2 were used. For both B001 and B002:

- all display-mode calls returned true;
- HLR and HLV geometry remained stable after save/reopen;
- view scale and sheet location remained identical;
- HLR visible supports were fully covered by HLV;
- Front produced no hidden candidate;
- Top and Right each produced two hidden line supports;
- no hidden circle/tessellation difference appeared.

## Semantic Provenance

HLR geometry is labelled `VISIBLE` with source `HLR_CAPTURE`. Only canonical
`HLV support − HLR support` is labelled `HIDDEN`, with source
`HLV_MINUS_HLR` and confidence 1.0. Center marks remain in the annotation
channel as `CENTERMARK`; they are not projected model edges. Without a
successful matched HLV/HLR run, projected primitives remain `UNKNOWN` and
Level 2B cannot pass.

## B001 Regression

| Gate | Result |
| --- | --- |
| 3D / B-Rep | PASS |
| Level 1 | PASS |
| Level 2A | PASS (all view support IoU = 1.0) |
| Level 2B | PASS (`HLV_MINUS_HLR`, 4 hidden supports, 0 unknown) |

## B002 Regression

| Gate | Result |
| --- | --- |
| 3D / B-Rep | PASS |
| Level 1 | PASS |
| Level 2A | PARTIAL (real Top/Right support overflow) |
| Level 2B | PARTIAL (hidden/visible provenance established; 2 expected centerlines absent) |

B002 has four proven hidden supports and zero unknown projected primitives.
Its two requested Front centerlines are not present as independently inspected
center-line annotations; the observed center mark is not promoted to a
different semantic type.

## Quality Gate

Targeted v0.3 unit tests: `18 passed`.

Full `python -m pytest`: `495 passed, 2 failed, 15 skipped`, 26 warnings, in
16.39 seconds. The two unchanged failures belong to the temporary copied
upstream tree:

1. `test_discover_installation_supports_injected_filesystem` assumes a
   hard-coded AutoCAD discovery candidate not present in this environment.
2. `test_release_check_passes_current_tree` expects a bundled-skill directory
   intentionally absent from this main project's migration state.

Neither expected result was edited, and neither failure is caused by v0.3.

## Decision

**C — support matching and canonicalization are working, but B002 contains a
real input-versus-regenerated visible-support mismatch.** Hidden/visible
provenance is reliable; center-line annotation completeness is not. Benchmark
003 and feature expansion remain frozen until B002's projection contract is
resolved without weakening the matcher.

## Git branch

Development is isolated on `feat/semantic-roundtrip`. The branch uses the
repository-specific SSH-over-443 remote because GitHub HTTPS is unavailable on
this host.
