# solidworks-main-skill progress report

## Current benchmark status

- B001-B005: **COMPLETE**
- B006: **PASS_CANDIDATE**
- Release status: **`v0.6-benchmark-006` baseline freeze**
- Baseline status: **merge validated**

The B006 decision is limited to the defined `PART_FEATURE_PATTERN` benchmark:
one BaseBlock, one offset through-hole seed, and one four-occurrence native
linear pattern. The main-branch merge review and post-merge regression passed;
the `v0.6-benchmark-006` tag identifies this reviewed baseline without
broadening B006 into general Pattern reconstruction support.

## v0.5 B005 Multi Feature Interaction

The B005 merge at `aef209a3139d034f6a1bff0b98ff8e95cd92ab76` passed
post-merge `python -m pytest -v`: 565 passed, 15 skipped, 2 deselected,
0 failed. Real SolidWorks 2024 SP04 reruns on that commit passed Backend,
B-Rep, Level 1, Level 2A, and Level 2B for B001–B005. B005 exact ownership
passed before and after reopen, with UNKNOWN=0 and UNATTRIBUTED=0.

Scope is limited to **BaseBlock + Offset Through Hole + Offset Straight Slot**:
100×60×20 mm base, Ø20 through hole at (-25,-10), and disjoint L40×W20 R10
X-major through slot at (15,8). Evidence binding and operation provenance
preserve separate Hole and Slot identities through B-Rep and drawing roundtrip.
Complex parts and intersecting cuts are outside the validated scope.

See `docs/V0.5_BENCHMARK_005_RELEASE.md` and its post-merge evidence snapshots.
The SW2024 slot-width `UPSTREAM_GAP` remains open; third-party backend source
and existing matcher tolerances were not changed for this release.

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

## B002 Projection Contract Audit

The former B002 v0.2 reference was `REFERENCE_INVALID`. Exact SolidWorks API
correspondence proved that the 60 mm Top and 40 mm Right overflow intervals are
parts of full visible BaseBlock exterior edges. They were not reconstruction or
matcher errors. The invalid input is preserved under `benchmarks/archive`, and
the active v0.3 reference records its integrity history and audit link.

No threshold changed. With the corrected projection contract, Front, Top, and
Right/Left-frame support IoU are all 1.0; missing and overflow lengths are all
0 mm. Top and Right have `SEGMENTATION_DIFFERENT`, because the structured input
splits a continuous support while SolidWorks returns one model-edge polyline;
their union geometry is exactly equivalent.

## Support-to-3D Edge Trace

`ProjectionSupportTracer` uses the documented `IView.GetPolylines7` edge array,
then follows ordinary edges through adjacent faces to owning features.

| View / audited interval | Exact source 3D edge (mm) | Adjacent owners | Projection result |
| --- | --- | --- | --- |
| Top `(20,20)→(80,20)`, 60 mm | `(50,30,0)→(-50,30,0)` | BaseBlock / BaseBlock | Full `(100,20)→(0,20)` visible edge |
| Right `(20,10)→(20,50)`, 40 mm | `(50,-30,0)→(50,30,0)` | BaseBlock / BaseBlock | Full `(20,0)→(20,60)` visible edge |

Both traces have `correspondence=EXACT` and
`provenance=HLR_CAPTURE_GETPOLYLINES7`. Two independent read-only reopen runs
produced byte-identical trace JSON. The same result remained after the final
B002 model and drawing regeneration on 2026-09-04.

## Reference Integrity

The original reference incorrectly trimmed BaseBlock exterior supports as if
the centered TopBoss occluded them. The corrected reference adds only the two
proven intervals, preserves the old JSON verbatim, supplies a machine-readable
history status, and has dedicated regression tests. See
`docs/B002_REFERENCE_AUDIT.md`. A future mismatch must use
`REFERENCE_INVALID` only when comparable evidence proves the reference itself
is wrong; it must not be reported as a reconstruction failure.

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

## Center Semantic Contract

`CENTERMARK`, `CENTERLINE`, and reasoning-only `AXIS` are separate types. Hole
center indication requires `CENTERMARK`; an axis indication or revolved-shaft
axis requires `CENTERLINE`; an inference guide is `AXIS` and never counts as a
drawing annotation. No type substitutes for another.

B002's former Front crosshair was a semantic aid around the face-on hole, not
two required CenterLine entities. The active contract now requires one Front
CenterMark. The final real drawing contains one CenterMark and zero CenterLine
objects, satisfying `1/1` and `0/0`. Standard-view creation and annotation
insertion are distinct APIs, so future deterministic delivery must explicitly
insert and read back the required annotation rather than rely on template
defaults. See `docs/CENTER_SEMANTIC_CONTRACT.md`.

## B002 Regression

| Gate | Result |
| --- | --- |
| 3D / B-Rep | PASS |
| Level 1 | PASS |
| Level 2A | PASS (all support IoU = 1.0; no missing/overflow) |
| Level 2B | PASS (`HLV_MINUS_HLR`, 4 hidden supports, 0 unknown, CenterMark 1/1) |

B002 has four proven hidden supports and zero unknown projected primitives.
Its corrected reference has `history_status=REFERENCE_INVALID` and current
`status=PASS`.

## pytest Migration Cleanup

Two exact migration-only node IDs are marked `upstream_compat` at collection:
the fixed AutoCAD-path assumption and the external desktop bundled-skill
snapshot check. They are deselected from the main-project gate, not deleted or
skipped. Every other test in those source files remains in the normal run.

`python -m pytest -m upstream_compat -v --tb=short` still reproduces both
failures, preserving the migration evidence. Details and removal conditions
are in `docs/UPSTREAM_TEST_BOUNDARY.md`.

## Quality Gate

Pre-merge full `python -m pytest -v`: `500 passed, 15 skipped, 2 deselected,
0 failed`, 26 warnings, in 17.82 seconds.

Real SolidWorks 2024 SP04 reruns on 2026-09-04:

| Gate | B001 | B002 |
| --- | --- | --- |
| Backend / save / reopen | PASS | PASS |
| 3D / B-Rep | PASS | PASS |
| Level 1 structured projection | PASS | PASS |
| Level 2A vector geometry | PASS | PASS |
| Level 2B semantics | PASS | PASS |
| UNKNOWN projected primitives | 0 | 0 |

## Final Quality Gate

- B001 all required gates: PASS.
- B002 prior reference: `REFERENCE_INVALID`, evidence preserved and audited.
- B002 corrected reference and regression: all required gates PASS.
- Main-project `python -m pytest`: 0 failed.
- Benchmark 003 remained frozen throughout this gate.

## Decision

**B — the B002 reference itself was wrong; it was corrected with exact
source-edge evidence, archived history, semantic-contract clarification, and
regression coverage. B001 and B002 now pass the complete v0.3 gate without
weakening any matcher threshold.**

## Git branch

Development was isolated on `feat/semantic-roundtrip` through the complete
pre-merge quality gate. The branch uses the
repository-specific SSH-over-443 remote because GitHub HTTPS is unavailable on
this host.

## v0.4 Benchmark 004 baseline

Benchmark 004 adds one bounded capability: translation/placement semantics for
the already-supported X-major straight through slot. A 40 × 20 mm R10 slot in
a 100 × 60 × 20 mm block is reconstructed at canonical model centre `(15,8)`
mm. Arbitrary rotation, Y-major slots, and blind slots remain outside scope.

Placement survives the complete engineering chain:

`ProjectionGraph (15,8) → FeatureGraph (15,8) → ModelingPlan (15,8) → real SolidWorks B-Rep (15,8)`.

The real B-Rep centre error is 0 mm. Cross-view X/Y conflicts are rejected,
missing position evidence remains ambiguous, and correct shape at an incorrect
position fails both reconstruction and roundtrip gates. Moving or scaling a
drawing view does not change canonical model-local placement.

Real SolidWorks 2024 SP04 evidence on 2026-09-05 includes rebuilt and reopened
SLDPRT, regenerated SLDDRW, Feature Tree, B-Rep measurement, HLR/HLV semantic
extraction, review images, and machine-readable benchmark results.

| Benchmark | Backend | B-Rep | Level1 | Level2A | Level2B | UNKNOWN |
| --- | --- | --- | --- | --- | --- | --- |
| B001 | PASS | PASS | PASS | PASS | PASS | 0 |
| B002 | PASS | PASS | PASS | PASS | PASS | 0 |
| B003 | PASS | PASS | PASS | PASS | PASS | 0 |
| B004 | PASS | PASS | PASS | PASS | PASS | 0 |

Post-merge `python -m pytest -v` result: 531 passed, 15 skipped, 2 deselected,
0 failed, with 26 warnings in 37.98 seconds. This capability is validated for
the defined benchmark scope; it is not a claim of general industrial drawing
reconstruction.

The known SolidWorks 2024 `create_semicircular_slot` width-semantics
`UPSTREAM_GAP` remains open and isolated in the main-project adapter. The
third-party external execution backend was not modified.
