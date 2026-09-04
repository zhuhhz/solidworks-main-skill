# B002 reference audit

## Decision

The original B002 projection contract is `REFERENCE_INVALID`. The reconstructed
SolidWorks model is correct; the v0.2 structured reference omitted visible
portions of two BaseBlock boundary edges and required two centerline
annotations where the intended semantic was one hole center mark.

The exact original input is preserved at
`experiments/three_view_reconstruction/benchmarks/archive/case_002_step_block.reference-invalid.v0.2.json`.
The active v0.3 reference contains the evidence-backed corrections below.

## Support-to-3D edge trace

The tracer uses `IView.GetPolylines7(1)`. SolidWorks returns an array of model
edges corresponding to the returned drawing polylines. Each ordinary edge is
then queried with `IEdge.GetStartVertex`, `IEdge.GetEndVertex`, and
`IEdge.GetTwoAdjacentFaces2`; every adjacent face is resolved with
`IFace2.GetFeature`. This is exact API correspondence, not a geometric guess.

| Missing reference support | Projected model edge | Source 3D edge (mm) | Adjacent face owners | Result |
| --- | --- | --- | --- | --- |
| Top `(20,20) → (80,20)`, horizontal, 60 mm | `(100,20) → (0,20)` | `(50,30,0) → (-50,30,0)` | `BaseBlock`, `BaseBlock` | Must be visible |
| Right `(20,10) → (20,50)`, vertical, 40 mm | `(20,0) → (20,60)` | `(50,-30,0) → (50,30,0)` | `BaseBlock`, `BaseBlock` | Must be visible |

Both source edges are the full outer boundary of the 100 × 60 × 20 mm base,
on faces owned by `BaseBlock`. The centered 60 × 40 boss does not trim these
front/side exterior edges in an orthographic Top or Right projection. The old
reference incorrectly removed the projected middle interval as though the boss
occluded it.

Machine-readable evidence:

- `projection_support_trace_run1.json`
- `projection_support_trace_run2.json`

The two files are byte-identical after independent read-only reopen runs. The
canonical roles are Top and Right in the third-angle generated drawing; input
Left is intentionally compared in the Right canonical frame. Visible semantics
come from HLR capture and the existing HLV-minus-HLR experiment reports zero
unknown projected primitives.

## Reference diff

1. Added Top visible support `(20,20) → (80,20)` so the full BaseBlock edge is
   represented.
2. Added Left-input/Right-frame visible support `(20,10) → (20,50)` for the
   second full BaseBlock edge.
3. Removed two Front `centerlines` from the active annotation requirement.
4. Added one explicit `CENTERMARK` requirement targeting `front circle:0`.
5. Added `reference_integrity.history_status = REFERENCE_INVALID` and linked
   this audit.

No matcher threshold or tolerance was changed.

## CenterMark / CenterLine audit

The external backend creates B002 views with `Create3rdAngleViews2`; it does
not call its explicit center-mark insertion routine in this benchmark. The
tested SolidWorks 2024 document nevertheless contains one Front CenterMark and
zero CenterLine entities, showing that the observed mark is template/document
behavior rather than proof that standard-view creation guarantees annotations.
Deterministic future drawing plans must call the specific insertion API and
verify entity readback.

For this benchmark, the circular Front projection represents the through-hole
face-on. Its required center semantic is therefore `CENTERMARK`, not two
`CENTERLINE` objects and not a reasoning-only `AXIS`.
