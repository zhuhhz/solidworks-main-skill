# B006 Merge Review and Baseline Freeze

## Git

- Repository: `zhuhhz/solidworks-main-skill`
- Target branch: `main`
- Source branch: `feat/benchmark-006-pattern`
- Source validation commit: `ec5bc1702d67c20d06ab6928511761aa295eedf0`
- Merge commit: `6e95bd70f2312993aed9f027581b7cb0a5615960`
- Merge parents:
  - `0370b3eebb4b382d54ae3ba71a530028fa0a4eba`
  - `ec5bc1702d67c20d06ab6928511761aa295eedf0`
- Merge mode: non-squash, non-rebase, `ort`, no conflicts
- Intended baseline tag after this report commit: `v0.6-benchmark-006`

The complete B006 commit history was retained. No benchmark contract, matcher,
threshold, golden geometry, B001-B005 implementation, or third-party backend
source was modified during merge review.

## Environment

- OS: Windows 11
- Python: 3.14.5
- pytest: 9.1.1
- SolidWorks evidence environment: 2024 SP04
- Test entry point: `python -m pytest`

## Validation status

| Benchmark | Status |
|---|---|
| B001 | PASS |
| B002 | PASS |
| B003 | PASS |
| B004 | PASS |
| B005 | PASS |
| B006 | PASS_CANDIDATE |

B006 remains `PASS_CANDIDATE` until this reviewed main-branch state is frozen
by the baseline tag. The decision is not broadened into general pattern
reconstruction support.

## B006 evidence gate

| Gate | Result |
|---|---|
| Backend | PASS |
| Save / close / read-only reopen | PASS |
| Feature Tree | PASS |
| Native SolidWorks `LPattern` | PASS |
| B-Rep | PASS |
| `PART_FEATURE_PATTERN` ownership contract | PASS |
| Level 1 | PASS |
| Level 2A | PASS |
| Level 2B | PASS |
| UNKNOWN | 0 |
| UNATTRIBUTED | 0 |

Ownership remains seed `API_EXACT` plus three generated occurrences at
`INSTANCE_EXACT`. Initial and read-only reopened mappings are identical.

Primary evidence:

- `docs/B006_PHASE_3_3_VALIDATION.md`
- `experiments/three_view_reconstruction/results/case_006_pattern/benchmark_results.json`
- `experiments/three_view_reconstruction/results/case_006_pattern/native_backend_evidence.json`
- `experiments/three_view_reconstruction/results/case_006_pattern/pattern_attributed_roundtrip.json`
- `experiments/hlv_hlr_semantics/results/case_006_pattern/semantic_diff.json`

## Post-merge regression

Command:

```powershell
python -m pytest -v
```

Result on `main` at merge commit `6e95bd70f2312993aed9f027581b7cb0a5615960`:

- 613 passed
- 15 skipped
- 2 deselected
- 0 failed
- 26 warnings
- exit code 0
- duration 56.97 seconds

## Remaining limitations

- Pattern ownership acceptance applies only to `PART_FEATURE_PATTERN`.
- Assembly Pattern is outside this contract and fails closed at the domain firewall.
- `INSTANCE_EXACT` is intentionally distinct from independent occurrence `API_EXACT`.
- SolidWorks Part Feature Pattern does not expose an independent occurrence object.
- The benchmark covers one BaseBlock, one through-hole seed, and one four-occurrence linear pattern only.
- This baseline does not establish general linear, circular, table-driven, sketch-driven, body, face, or assembly pattern reconstruction.

## Merge review decision

**BASELINE_READY**

The merge is clean, the full post-merge regression has zero failures, the real
SolidWorks evidence chain remains complete for the defined scope, and the
repository is ready for the `v0.6-benchmark-006` baseline tag. B006 remains
reported as `PASS_CANDIDATE`; this document does not declare a broader B006
PASS or begin B007.
