# Known limitations

- No PNG/JPG OCR or vision-model path is included.
- Hidden, visible and centre-line style classification is not yet proven from
  `IView.GetPolyLinesAndCurves` in the tested SolidWorks 2024 environment.
- Dependent Top/Right views report empty `GetOrientationName`; their canonical
  role currently comes from the recorded standard-view creation contract.
- Level 2B cannot PASS until each projected primitive has a demonstrated
  semantic provenance.
- B002's Top/Right graph does not match the actual regenerated line support;
  the validator correctly reports PARTIAL rather than altering input evidence.
- Complex surfaces, OCR, arbitrary drawings, ambiguous projections, and full
  engineering-drawing layout/dimension closure remain out of scope.
