# B006 Contract Migration Plan

Status: **PLANNING ONLY / NOT EXECUTED / AWAITING REVIEW**

Date: 2026-09-05  
Project: `solidworks-main-skill`  
Source proposal: `docs/B006_ACCEPTANCE_PROPOSAL.md`  
Target benchmark: B006 — SolidWorks Part Feature Linear Pattern

This document describes a future contract migration. It does not authorize or
perform code changes, golden-data changes, SolidWorks execution, commits,
merges, tags, or a B006 status change.

## 1. Migration objective

Replace the current B006 Phase 3 requirement:

```text
all occurrences == API_EXACT
```

with a domain-scoped exact-ownership gate:

```text
ownership_domain == PART_FEATURE_PATTERN
AND seed occurrence == API_EXACT
AND every generated occurrence == API_EXACT or INSTANCE_EXACT
AND PATTERN_ONLY == 0
AND OWNERSHIP_UNRESOLVED == 0
AND UNKNOWN == 0
AND UNATTRIBUTED == 0
AND all required native evidence and save/reopen checks pass
```

The migration changes the accepted proof form for generated instances of one
specific SolidWorks object model. It does not rename evidence levels, relax
their definitions, alter geometry tolerances, or accept ambiguous attribution.

Until implementation, review, regression, and real-evidence validation are
completed, B006 remains **NOT VALIDATED**.

## 2. Scope firewall

The revised rule applies only when all of the following are explicit:

```text
benchmark = B006
ownership_domain = PART_FEATURE_PATTERN
cad_system = SOLIDWORKS
pattern_kind = LINEAR_FEATURE_PATTERN
```

It must not apply to:

- B001–B005;
- ordinary Base, Hole, Slot, Boss, or multi-feature ownership;
- `ASSEMBLY_COMPONENT_PATTERN`;
- `PART_BODY_PATTERN` without a separate capability contract;
- mirror, circular, curve-driven, sketch-driven, table-driven, or variable
  patterns without their own benchmark evidence;
- another CAD backend merely because it uses the word `pattern`.

Missing or unknown ownership domain must fail closed. It must not default to
`PART_FEATURE_PATTERN`.

## 3. Existing implementation points affected by a future migration

No changes are made in this planning task. If the proposal is approved, the
smallest expected implementation surface is:

| Existing file | Future migration responsibility | Constraint |
|---|---|---|
| `experiments/three_view_reconstruction/validation/b006_phase3.py` | Replace the all-`API_EXACT` Phase 3 predicate with the domain-scoped mixed exact gate. | Must reject missing/wrong domain and incomplete evidence. |
| `experiments/three_view_reconstruction/validation/pattern_contract.py` | Enforce seed `API_EXACT`, permit generated `API_EXACT`/strict `INSTANCE_EXACT`, and reject both diagnostic states. | Do not generalize this policy into B001–B005 validators. |
| `experiments/three_view_reconstruction/backend/pattern_ownership_probe.py` | Supply any mandatory domain/configuration/skipped-state evidence not already present. | Evidence collection only; no owner guessing or relabeling. |
| `experiments/three_view_reconstruction/drawing/pattern_drawing_attribution.py` | Report mixed exact strength without making all-`API_EXACT` the Part Pattern overall gate. | Resolve the existing worktree conflict separately before migration. |
| `experiments/three_view_reconstruction/run_b006_phase3.py` | Compose the revised B006 result only after every unchanged gate and new ownership gate pass. | Must not declare B006 PASS from API success alone. |

No new Engine, Manager, Resolver, framework, or parallel acceptance pipeline is
needed. The migration should remain inside the existing B006 validators and
tests.

## 4. Existing tests that need adjustment

### 4.1 `tests/unit/test_b006_phase3_validation.py`

The current test `test_real_gate_requires_api_exact_for_every_occurrence` encodes
the superseded predicate and must be replaced with explicit domain cases.

Required replacement coverage:

1. `PART_FEATURE_PATTERN` with seed `API_EXACT` and three generated
   `INSTANCE_EXACT` occurrences passes the ownership portion of the gate.
2. `PART_FEATURE_PATTERN` with all four occurrences `API_EXACT` also passes.
3. The same evidence without an explicit ownership domain fails closed.
4. The same mixed evidence under `ASSEMBLY_COMPONENT_PATTERN` fails.
5. A seed occurrence marked only `INSTANCE_EXACT` fails.
6. Any generated occurrence marked `PATTERN_ONLY` fails.
7. Any occurrence marked `OWNERSHIP_UNRESOLVED` fails.
8. Initial and reopened ownership mappings that differ fail.

The existing synthetic backend fixture will need to express occurrence-level
rows and mandatory evidence fields rather than only aggregate counts. Aggregate
counts alone are insufficient to prove that the seed is `API_EXACT` or that
each generated instance has a complete evidence chain.

### 4.2 `tests/unit/test_b006_pattern_contract.py`

The current parametrized `test_exact_ownership_states` accepts a fixture in
which all occurrences share the same state. That is too broad for the revised
B006 acceptance contract because it allows a seed-only `INSTANCE_EXACT` chain.

It should be split into:

- a row/schema-level test proving that both exact labels remain valid semantic
  values;
- a B006 contract test requiring the seed row to be `API_EXACT`;
- a B006 contract test permitting generated rows to be `INSTANCE_EXACT`;
- a test proving all-generated-`API_EXACT` remains valid;
- a test proving an `INSTANCE_EXACT` seed does not pass B006.

The ownership fixture should represent the real native relationship:

```text
seed occurrence native owner = seed_hole_001
generated occurrence native owner = pattern_001
```

This is a unit-fixture correction, not a golden geometry change.

The following tests in this file remain semantically valid and need no expected
result change:

- four instances and role serialization;
- wrong count;
- missing instance;
- wrong spacing;
- wrong direction;
- missing seed;
- instance-direct-to-Base dependency violation;
- order-variant equivalence;
- reversed operation dependency;
- operation provenance;
- identity and geometry mutations;
- `PATTERN_ONLY` and `OWNERSHIP_UNRESOLVED` rejection;
- ownership swap/missing-row rejection;
- exact label without identity evidence rejection.

Only fixtures or helper signatures should change where necessary to carry an
explicit ownership domain and complete instance evidence.

### 4.3 B006 result-composition tests

If result composition currently tests `strict_api_exact_status` as the single
ownership result, that assertion must be separated into:

```text
strict_api_exact_status       # remains diagnostic and may be FAIL
part_pattern_acceptance_status # new domain-scoped acceptance result
```

The migration must preserve the truthful evidence:

```text
API_EXACT = 1
INSTANCE_EXACT = 3
strict_api_exact_status = FAIL
```

A B006 Part Pattern acceptance result may pass without rewriting those facts.

## 5. Existing tests that must remain unchanged

### 5.1 B006 structured geometry and evidence binding

`tests/unit/test_b006_pattern_evidence.py` should remain unchanged because it
tests ProjectionGraph evidence completeness, explicit attribution, overlap
preservation, and conflict handling—not native ownership acceptance.

Its current protections remain mandatory:

- wrong instance position fails without owner reassignment;
- missing evidence returns `UNATTRIBUTED`;
- missing seed evidence fails;
- count mismatch fails before attribution;
- overlapping `ownership_set` is preserved;
- swapped instance claims fail;
- incomplete overlap ownership fails.

### 5.2 Existing B006 negative controls

The existing Phase 3 negative controls remain unchanged:

- wrong count;
- wrong spacing;
- wrong direction;
- missing seed;
- missing instance;
- wrong native pattern type.

They validate Pattern structure and geometry, not the revised ownership proof
form.

### 5.3 Level 1, Level 2A, and Level 2B

The following expectations remain frozen:

- Base envelope;
- hole count, diameter, position, axis, and through extent;
- native Pattern count, spacing, direction, and feature type;
- three standard views;
- vector geometry matching;
- HLR/HLV semantic extraction;
- `UNKNOWN == 0`;
- `UNATTRIBUTED == 0`;
- coincident projections preserve `ownership_set`.

No matcher tolerance or expected primitive geometry changes are part of this
migration.

### 5.4 B001–B005

Every B001–B005 unit, regression, benchmark, integration, golden-data, B-Rep,
Drawing, and ownership test remains unchanged.

In particular:

- B005 direct Base/Hole/Slot feature ownership remains `API_EXACT`;
- `INSTANCE_EXACT` is not added to the generic B005
  `OwnershipEvidence` acceptance set;
- no B001–B005 expected result is reclassified;
- no historic benchmark report is rewritten.

## 6. Mandatory new negative tests

The migration is incomplete unless all cases below are executable and fail for
the specified reason.

| Negative case | Expected result |
|---|---|
| Ownership domain missing | `OWNERSHIP_DOMAIN_REQUIRED` |
| Unknown ownership domain | `OWNERSHIP_DOMAIN_UNSUPPORTED` |
| Mixed Part Pattern evidence labeled as `ASSEMBLY_COMPONENT_PATTERN` | Fail; `INSTANCE_EXACT` must not leak into Assembly acceptance |
| Seed marked `INSTANCE_EXACT` | `SEED_API_IDENTITY_REQUIRED` |
| Generated occurrence is `PATTERN_ONLY` | `INSTANCE_IDENTITY_UNPROVEN` |
| Generated occurrence is `OWNERSHIP_UNRESOLVED` | `OWNERSHIP_UNRESOLVED` |
| Generated occurrence has no Pattern persistent reference | `PATTERN_REFERENCE_MISSING` |
| Generated occurrence has no Seed persistent reference | `SEED_REFERENCE_MISSING` |
| Generated B-Rep entity has no persistent reference | `ENTITY_REFERENCE_MISSING` |
| Instance index missing, duplicated, or outside native count | `INSTANCE_INDEX_INVALID` |
| `GetTransform` evidence missing | `INSTANCE_TRANSFORM_MISSING` |
| Transform differs from the declared occurrence | `INSTANCE_TRANSFORM_MISMATCH` |
| Two occurrences satisfy the same complete transform/entity evidence | `INSTANCE_IDENTITY_AMBIGUOUS` |
| Native owner is neither expected seed nor expected Pattern | `NATIVE_OWNER_MISMATCH` |
| Initial and reopened occurrence mapping differs | `REOPEN_OWNERSHIP_MISMATCH` |
| Persistent reference cannot be restored after reopen | `PERSISTENT_REFERENCE_RESTORE_FAILED` |
| Configuration differs between collection and reopen | `CONFIGURATION_MISMATCH` |
| Skipped/suppressed state differs | `PATTERN_STATE_MISMATCH` |
| `nearest_geometry_used == true` | `PROHIBITED_ATTRIBUTION_METHOD` |
| `name_matching_used == true` | `PROHIBITED_ATTRIBUTION_METHOD` |
| `array_order_used == true` or face enumeration order is used | `PROHIBITED_ATTRIBUTION_METHOD` |
| Coincident drawing support is forced to one owner | `OVERLAP_OWNERSHIP_LOSS` |
| `UNKNOWN > 0` | Overall B006 failure |
| `UNATTRIBUTED > 0` | Overall B006 failure |

Where the current result vocabulary does not yet contain one of these exact
codes, implementation review may consolidate codes into existing precise
categories. It must not collapse them into a generic PASS/FAIL that hides the
failure cause.

## 7. INSTANCE_EXACT automatic acceptance conditions

`INSTANCE_EXACT` must be computed from evidence. A caller-provided label alone
must never pass.

For each generated Part Feature Pattern occurrence, automatic acceptance
requires all of the following:

### Domain and model context

- ownership domain is exactly `PART_FEATURE_PATTERN`;
- CAD system and tested version are recorded;
- document and active configuration identities are recorded;
- the native feature type is a supported Part Feature Pattern type for this
  benchmark (`LPattern`/`LinearPattern`).

### Native Feature relationship

- Pattern Feature persistent reference resolves;
- Seed Feature persistent reference resolves;
- Pattern definition identifies the expected Seed Feature;
- native count, spacing, signed direction, and skipped-item state match the
  FeatureGraph and ModelingPlan;
- the generated face reports the expected native Pattern owner;
- the seed face reports the expected seed owner.

### Instance relationship

- the occurrence has an explicit, unique instance ID;
- instance index is present and valid in the native Pattern definition;
- the API supplies a transform for that index;
- applying the transform to seed geometry agrees exactly with the declared
  occurrence and its generated B-Rep entity;
- exactly one occurrence satisfies the complete evidence chain;
- the generated B-Rep face/edge has a persistent reference;
- no identity decision uses nearest geometry, names, or enumeration order.

### Lifecycle and drawing relationship

- the same persistent Pattern, Seed, and B-Rep entities resolve after read-only
  reopen;
- the reopened instance index, transform, owner, and geometry association are
  unchanged;
- projected primitives map to the same occurrence or explicit overlap
  `ownership_set`;
- Level 2 attribution has zero `UNKNOWN` and zero `UNATTRIBUTED` results.

### Result rule

```text
if every condition is true:
    ownership = INSTANCE_EXACT
else if only native Pattern membership is proven:
    ownership = PATTERN_ONLY
else:
    ownership = OWNERSHIP_UNRESOLVED
```

There is no permitted automatic promotion from `PATTERN_ONLY` to
`INSTANCE_EXACT` based on proximity or expected count.

## 8. API_EXACT retention points

`API_EXACT` remains the strongest ownership level and must be retained in all
places where SolidWorks exposes direct identity.

### Required in B006

- seed occurrence ownership;
- Seed Feature persistent identity;
- Pattern Feature persistent identity;
- any generated occurrence for which a future SolidWorks API actually exposes
  a direct occurrence object.

### Required outside B006

- B001–B005 direct Feature ownership where already required;
- future `ASSEMBLY_COMPONENT_PATTERN` occurrences when represented by direct
  `IComponent2` identity;
- future Part Body Pattern if capability research proves direct persistent Body
  occurrence identity;
- any backend/domain whose native API exposes an independent occurrence object.

`INSTANCE_EXACT` is never the global fallback for an `API_EXACT` failure. It is
valid only under an explicitly approved domain contract.

## 9. Assembly Pattern extension guard

Future Assembly Pattern support must be independently planned and validated.
The migration should leave a hard guard equivalent to:

```text
if ownership_domain == ASSEMBLY_COMPONENT_PATTERN:
    generated occurrence must be API_EXACT
```

Required isolation tests:

1. An Assembly Pattern component with direct `IComponent2` identity passes as
   `API_EXACT`.
2. The same component labeled only `INSTANCE_EXACT` fails.
3. A Part Pattern mixed chain cannot be replayed under the Assembly domain.
4. Domain omission cannot infer Part versus Assembly from feature names.

These tests reserve the stronger future model without implementing Assembly
Pattern in B006.

## 10. Migration sequence after approval

This sequence is a plan, not an instruction executed by this task.

1. Restore a clean B006 working state and resolve the pre-existing conflict
   separately from the contract migration.
2. Freeze B001–B005 and B006 golden geometry by hash or clean-tree verification.
3. Add the domain discriminator and exact evidence requirements at the existing
   B006 gate boundary.
4. Update the two existing B006 ownership test files; avoid a new test framework.
5. Add the domain-leakage and evidence-removal negative cases.
6. Run the smallest unit set first:

   ```powershell
   python -m pytest tests/unit/test_b006_pattern_contract.py -v
   python -m pytest tests/unit/test_b006_phase3_validation.py -v
   python -m pytest tests/unit/test_b006_pattern_evidence.py -v
   ```

7. Run the full non-COM regression with the standard entry point:

   ```powershell
   python -m pytest -v
   ```

8. Only in a separately authorized task, run real SolidWorks B006 validation,
   save/reopen, B-Rep, Drawing, Level 1, Level 2A, and Level 2B.
9. Review the resulting evidence without rewriting ownership labels.
10. Decide B006 status in a separate Final Validation Review.

## 11. Expected test impact summary

| Area | Expected action |
|---|---|
| B006 Phase 3 all-`API_EXACT` gate test | Replace with domain-scoped mixed exact matrix |
| B006 Pattern ownership fixture | Adjust seed/native-owner realism and explicit domain |
| B006 PatternEvidence tests | No change |
| B006 geometry/dependency/provenance tests | No change |
| B006 existing negative controls | No change |
| B006 new ownership negatives | Add |
| Level 1 / Level 2A / Level 2B matchers | No change |
| B001–B005 tests and golden data | No change |
| Future Assembly Pattern | No implementation; add only isolation expectations when migration occurs |

## 12. Review decision requested

Approval of this migration plan would authorize a later, bounded contract-change
task with the following invariant:

```text
Only PART_FEATURE_PATTERN generated occurrences may satisfy B006 with a strict
INSTANCE_EXACT proof. API_EXACT remains mandatory for the seed, B001–B005 direct
ownership, and future Assembly Pattern occurrences with native component identity.
```

No implementation or validation status change is performed by this document.
B006 remains **NOT VALIDATED** pending review and subsequent authorized work.
