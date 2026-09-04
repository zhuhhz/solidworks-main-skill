# Known limitations

- No PNG/JPG OCR or vision-model path is included.
- Visible and hidden semantics are proven for B001/B002 by matched HLR/HLV
  extraction; direct per-primitive style metadata is still unavailable.
- Dependent Top/Right views report empty `GetOrientationName`; their canonical
  role currently comes from the recorded standard-view creation contract.
- Center-line annotations remain incomplete: a center mark is not treated as
  an independent center line.
- B002's Top/Right graph has 60/40 mm of real regenerated support overflow;
  the validator reports PARTIAL rather than altering input evidence or
  weakening thresholds.
- Complex surfaces, OCR, arbitrary drawings, ambiguous projections, and full
  engineering-drawing layout/dimension closure remain out of scope.
