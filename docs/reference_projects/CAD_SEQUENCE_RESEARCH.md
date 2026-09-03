# CAD operation sequence research

Drawing2CAD encodes CAD as a vectorized command sequence and pairs it with normalized SVG view sequences. TriView2CAD includes executable CAD scripts and parameter JSON alongside the B-Rep target. Both support the decision to retain a serializable, backend-neutral plan rather than emitting SolidWorks calls from a parser.

## v0.2 compatible proposal

Do not replace Benchmark 001/002 `ModelingOperation`. Introduce `CADOperation` as an additive normalized form and provide a lossless adapter from current operations:

```json
{
  "id":"op-03", "kind":"CUT_EXTRUDE", "depends_on":["op-02"],
  "sketch":{"support":{"kind":"REFERENCE_PLANE","id":"Plane_Boss_Top"},
            "profiles":[{"kind":"CIRCLE","center":[0,0],"diameter_mm":20}]},
  "extent":{"kind":"THROUGH_ALL","direction":"NEGATIVE_NORMAL"},
  "semantic_role":"THROUGH_HOLE", "expected_effect":{"remove_material":true},
  "evidence_refs":["hyp-hole-1"]
}
```

Core kinds: `SKETCH`, `EXTRUDE`, `CUT_EXTRUDE`, `REVOLVE`, `HOLE`, `FILLET`, `CHAMFER`, `PATTERN`, `REFERENCE_PLANE`. Separate semantic role from kernel operation: an ISO through-hole may compile to a Hole Wizard or a circular CutExtrude depending on backend capability.

Backward compatibility: compile `base_extrude`, `boss_extrude`, and `cut_extrude_through_circle` into the v0.2 form in a new adapter; continue executing the existing plan unchanged until regression results match.
