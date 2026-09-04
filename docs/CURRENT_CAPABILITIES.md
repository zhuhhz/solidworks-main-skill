# Current capabilities

| Capability | Status | Evidence |
| --- | --- | --- |
| Structured three-view input consistency | Verified | B001, B002 |
| Block, stepped boss, Ø20 through-hole inference | Verified in scoped benchmarks | B001, B002 |
| Backend-neutral modeling plan | Verified | persisted benchmark results |
| External SolidWorks adapter execution | Verified | saved SLDPRT, Feature Tree, B-Rep |
| Third-angle view regeneration | Verified | generated SLDDRW |
| Level 1 structured roundtrip | Verified | B001, B002 |
| Canonical numeric view frames | Verified | English/Chinese names, translation and 1:1/1:2/2:1 tests |
| Level 2A support-coverage line/circle comparison | B001 verified; B002 partial due real support overflow | actual IView extraction |
| HLV/HLR visible and hidden provenance | Verified for B001/B002 | matched save/reopen experiment |
| Level 2B drawing semantics | B001 and B002 verified | B002 explicitly requires one hole `CENTERMARK`; `CENTERLINE` remains a distinct contract |

See [PROJECT_PROGRESS_REPORT.md](PROJECT_PROGRESS_REPORT.md) for exact
limitations and test-date context.
