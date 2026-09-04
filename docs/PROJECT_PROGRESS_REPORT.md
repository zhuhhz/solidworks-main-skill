# solidworks-main-skill progress report

## Identity and boundary

`solidworks-main-skill` owns engineering reasoning and validation.  The
third-party `wzyn20051216/solidworks-automation-skill` is used only as an
external SolidWorks execution backend through the experiment adapter.

## Tested on 2026-09-04

| Item | Result |
| --- | --- |
| Benchmark 001: block 100×60×40, Ø20 through hole | 3D PASS; Level 1 PASS; Level 2A PASS; Level 2B PARTIAL |
| Benchmark 002: stepped block, Ø20 through hole | 3D PASS; Level 1 PASS; Level 2A PARTIAL; Level 2B PARTIAL |
| Saved/reopened SLDPRT and B-Rep evidence | PASS for B001/B002 |
| Regenerated third-angle three views | PASS for B001/B002 |

## Level-2 interpretation

Level 2A compares normalized projected lines and circles.  B001 passes after
an actual SW2024 probe established that `IView.GetPolyLinesAndCurves` returns
model metres even for a 1:2 sheet view.  B002 remains PARTIAL: the regenerated
Top/Right line segmentation does not equal the supplied graph, and that is
recorded rather than normalized away.

Level 2B is intentionally PARTIAL.  Center marks are independently observed,
but this API path has not demonstrated projected line-style provenance for
visible, hidden, and center lines.  `UNKNOWN` is retained for those primitives.

## Next evidence-driven work

1. Test HLV/HLR display-mode differential extraction without changing the
   benchmark expected geometry.
2. Add topology-backed hidden-line corroboration.
3. Add a canonical segment split/merge comparison only where it preserves the
   same geometric support.
4. Add Benchmark 003 only after the Level-2 rules have an explicit slot/slot
   acceptance contract.

## GitHub delivery state

The local remote is `zhuhhz/solidworks-main-skill`.  GitHub API authentication
works, but the host's Git HTTPS connection to `github.com:443` is reset; local
commits are retained and publishing is `NETWORK_BLOCKED` until connectivity is
restored.  No repeated push retry is part of benchmark execution.
