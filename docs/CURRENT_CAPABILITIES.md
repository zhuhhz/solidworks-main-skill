# Current capabilities

| Capability | Status | Evidence |
| --- | --- | --- |
| Structured three-view input consistency | Verified | B001–B004 |
| Block, stepped boss, Ø20 through-hole inference | Verified in scoped benchmarks | B001, B002 |
| X-major straight through-slot inference | Verified in scoped benchmarks | B003, B004 |
| Offset feature placement preservation | Verified in scoped benchmark | B004; ProjectionGraph → FeatureGraph → ModelingPlan → B-Rep centre `(15,8)` mm |
| Cross-view slot-position consistency | Verified in scoped benchmark | B004 X/Y conflict and ambiguity regressions |
| Backend-neutral modeling plan | Verified | persisted benchmark results |
| External SolidWorks adapter execution | Verified | saved SLDPRT, Feature Tree, B-Rep |
| Third-angle view regeneration | Verified | generated SLDDRW |
| Level 1 structured roundtrip | Verified | B001–B004 |
| Canonical numeric view frames | Verified | English/Chinese names, translation and 1:1/1:2/2:1 tests |
| Level 2A support-coverage line/circle/arc comparison | Verified in scoped benchmarks | B001–B004 actual IView extraction and canonical matching |
| HLV/HLR visible and hidden provenance | Verified in scoped benchmarks | B001–B004 matched save/reopen experiment |
| Level 2B drawing semantics | Verified in scoped benchmarks | B001–B004; B002 explicitly requires one hole `CENTERMARK`; `CENTERLINE` remains distinct |

See [PROJECT_PROGRESS_REPORT.md](PROJECT_PROGRESS_REPORT.md) for exact
limitations and test-date context.
