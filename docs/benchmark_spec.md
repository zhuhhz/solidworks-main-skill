# Benchmark specification

## Case 001

100 x 60 x 40 block with a centred Ø20 through-hole. It establishes Level 1 structured projection invariants.

## Case 002

Stepped block: 100 x 60 x 20 base, 60 x 40 x 20 upper boss, and centred Ø20 through-hole. Required plan: base extrusion, second boss extrusion, then cut extrusion.

## Case 003

100 x 60 x 20 plate with a Ø20 through-hole and 40 x 10 rectangular slot. Required plan: base extrusion plus two cut extrusions.

## Case 004

Offset X-major straight through slot in a 100 x 60 x 20 mm block. The slot has 40 mm overall length, 20 mm width, R10 ends, and canonical model centre `(15, 8)` mm. This case validates slot placement semantics, cross-view position consistency, B-Rep placement measurement, and drawing roundtrip for the defined benchmark scope.

## Verified benchmark registry

Real SolidWorks 2024 SP04 evidence was regenerated and checked on 2026-09-05.

| Benchmark | Backend | B-Rep | Level1 | Level2A | Level2B |
| --- | --- | --- | --- | --- | --- |
| B001 | PASS | PASS | PASS | PASS | PASS |
| B002 | PASS | PASS | PASS | PASS | PASS |
| B003 | PASS | PASS | PASS | PASS | PASS |
| B004 | PASS | PASS | PASS | PASS | PASS |

Level 2 is not passed until generated drawing visible/hidden primitives are extracted, normalized in view-local coordinates, canonicalized, and matched to input primitives.
