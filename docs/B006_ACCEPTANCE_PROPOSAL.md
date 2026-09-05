# B006 Benchmark Acceptance Revision Proposal

Status: **PROPOSAL ONLY / NOT APPROVED / CONTRACT NOT YET CHANGED**

Date: 2026-09-05  
Project: `solidworks-main-skill`  
Benchmark: B006 — Part Feature Linear Pattern  
Defined scope: `BaseBlock + Seed Through Hole + 4-instance Linear Pattern`

This document proposes an acceptance-policy revision only. It does not change
implementation code, benchmark golden data, matcher tolerances, existing evidence,
or the accepted status of any benchmark.

## 1. Decision summary

**Recommendation: revise the B006 acceptance contract conditionally.**

For a SolidWorks **Part Feature Pattern**, accept `INSTANCE_EXACT` as the highest
platform-achievable exact ownership level for generated pattern copies, provided
that every mandatory evidence condition in this proposal passes. Retain
`API_EXACT` as the stronger level and require it wherever SolidWorks exposes a
direct occurrence object.

This is not a proposal to:

- rename `INSTANCE_EXACT` to `API_EXACT`;
- treat `PATTERN_ONLY` as instance ownership;
- permit nearest-geometry, feature-name, or enumeration-order attribution;
- weaken B001–B005 ownership requirements;
- declare B006 accepted before the revised contract is approved and rerun.

Until this proposal is approved and the existing evidence is reviewed against
the revised gate, B006 remains **NOT VALIDATED**.

## 2. Background and capability finding

The B006 capability research established that the public SolidWorks 2024 Part
Feature Pattern API exposes:

- a native Pattern `IFeature`;
- the seed feature through the pattern definition and
  `IFace2.GetPatternSeedFeature`;
- instance count, spacing, skipped-item information, and an API instance index;
- `ILinearPatternFeatureData.GetTransform(instance)`;
- persistent references for the seed feature, pattern feature, and generated
  B-Rep faces/edges.

It does not expose an independent Part Pattern occurrence object that can be:

1. returned as the direct owner of a generated face or edge;
2. assigned its own occurrence-level persistent reference; and
3. recovered after save/reopen as an independent occurrence.

For generated copies, `IFace2.GetFeature` returns the native `LPattern` feature.
The seed face is directly owned by the seed feature. Consequently, an
all-occurrences-`API_EXACT` gate is unsatisfiable for this SolidWorks object model,
even when the native pattern, topology, instance transforms, and reopened model
are all correct.

## 3. Ownership semantic levels

The levels are ordered by evidence strength. They are not interchangeable labels.

| Level | Meaning | Required evidence | Acceptance role |
|---|---|---|---|
| `API_EXACT` | SolidWorks directly exposes the occurrence/feature object and its persistent identity, and the relevant entity resolves to that owner without inferred instance selection. | Direct API object, stable identity, direct ownership, save/reopen consistency. | Strongest level; always acceptable where applicable. |
| `INSTANCE_EXACT` | SolidWorks exposes the native pattern, seed, instance index/transform, and persistent B-Rep entity, but no independent occurrence object. These native facts form one unique and reproducible instance attribution. | Complete compound evidence defined in section 5; no heuristic owner selection. | Proposed highest acceptable level for generated copies in a Part Feature Pattern only. |
| `PATTERN_ONLY` | The entity is proven to belong to the native Pattern feature, but no unique generated instance is proven. | Pattern owner only, or multiple unresolved candidate instances. | Diagnostic only; never satisfies B006. |
| `OWNERSHIP_UNRESOLVED` | The available evidence cannot reliably establish even the required pattern/instance relationship. | Missing, conflicting, ambiguous, or non-reproducible evidence. | Failure. |

`INSTANCE_EXACT` must remain visibly distinct from `API_EXACT` in reports, JSON
evidence, matrices, and future release notes.

## 4. Why INSTANCE_EXACT is the reasonable maximum for Part Pattern

### 4.1 It is bounded by the native SolidWorks object model

The limitation is not missing project code. A Part Feature Pattern is represented
as one native Pattern feature plus indexed transforms. Generated copies do not
appear as independent occurrence objects. Additional wrappers cannot create a
native identity that SolidWorks does not expose.

### 4.2 It uses API facts, not geometric owner guessing

`INSTANCE_EXACT` is not a nearest-geometry fallback. The attribution begins with
an explicit instance identity from the FeatureGraph and is verified against all
of the following native facts:

```text
Pattern persistent reference
+ Seed persistent reference
+ API instance index
+ ILinearPatternFeatureData.GetTransform(instance)
+ generated B-Rep entity persistent reference
+ exact transformed topology/geometry agreement
+ save/reopen reproducibility
```

Geometry verifies an already-declared instance claim; it does not search for or
guess an owner.

### 4.3 It survives the lifecycle required by the benchmark

The B006 evidence contains the same four occurrence assignments before close and
after read-only reopen:

| Occurrence | Native face owner | Ownership level |
|---|---|---|
| seed occurrence | seed hole feature | `API_EXACT` |
| generated copy 1 | `LPattern` | `INSTANCE_EXACT` |
| generated copy 2 | `LPattern` | `INSTANCE_EXACT` |
| generated copy 3 | `LPattern` | `INSTANCE_EXACT` |

The existing evidence reports one `API_EXACT`, three `INSTANCE_EXACT`, and zero
unresolved occurrences in both states.

### 4.4 It preserves ambiguity instead of hiding it

If two candidates satisfy the same evidence, the result is not
`INSTANCE_EXACT`. It must become `PATTERN_ONLY` or `OWNERSHIP_UNRESOLVED`.
Likewise, coincident drawing projections retain an explicit `ownership_set`
rather than selecting one owner.

## 5. Proposed B006 Part Pattern acceptance contract

### 5.1 Domain declaration

The benchmark evidence must explicitly declare:

```text
ownership_domain = PART_FEATURE_PATTERN
cad_system = SOLIDWORKS
cad_version = 2024 SP04
```

The domain declaration prevents this policy from being applied automatically to
assembly component patterns, body patterns, mirror instances, or another CAD
backend.

### 5.2 Required ownership evidence for every occurrence

For the seed occurrence:

- direct seed feature identity must be `API_EXACT`;
- the seed feature persistent reference must resolve after reopen;
- its geometry must match the declared seed parameters.

For every generated copy, `INSTANCE_EXACT` is acceptable only if all conditions
below pass:

1. The native owner is the expected Pattern feature.
2. The Pattern feature is identified by a persistent reference, not a name.
3. The seed feature is identified by a persistent reference, not a name.
4. The API-reported total count, spacing, direction, and skipped-item state match
   the FeatureGraph and ModelingPlan.
5. The API instance index is valid in the native pattern definition.
6. `GetTransform(instance)` returns the expected native transform.
7. The generated B-Rep entity has its own persistent reference.
8. Applying the instance transform to the seed geometry identifies exactly one
   expected generated occurrence.
9. No second candidate satisfies the same complete evidence.
10. The same relation is reproduced after close and read-only reopen.
11. Configuration and suppression/skipped state are identical in both checks.
12. No feature-name, nearest-distance, raw face-array order, or Feature Tree
    display order is used as ownership evidence.

Failure of any condition prevents `INSTANCE_EXACT`.

### 5.3 Revised ownership gate

For B006 in `PART_FEATURE_PATTERN` scope, the proposed gate is:

```text
seed occurrence == API_EXACT
AND every generated occurrence == INSTANCE_EXACT or API_EXACT
AND PATTERN_ONLY count == 0
AND OWNERSHIP_UNRESOLVED count == 0
AND UNKNOWN count == 0
AND UNATTRIBUTED count == 0
AND save/reopen ownership relation is identical
AND all existing Backend, Feature Tree, B-Rep, Level 1, Level 2A,
    Level 2B, and negative-test gates pass
```

This proposal changes only the generated-copy acceptance predicate from
`API_EXACT only` to `API_EXACT or strictly proven INSTANCE_EXACT` within the
declared Part Feature Pattern domain.

### 5.4 Non-acceptable evidence

The following remain failures:

- owner resolves only to `LPattern`, without a unique instance chain;
- missing or non-restorable persistent reference;
- instance selected by nearest center or nearest face;
- instance selected by feature/display name;
- instance selected by B-Rep enumeration order;
- transform mismatch, duplicate transform candidate, or skipped-item conflict;
- different ownership result after reopen;
- any `PATTERN_ONLY`, `OWNERSHIP_UNRESOLVED`, `UNKNOWN`, or `UNATTRIBUTED` result;
- drawing overlap collapsed to an invented single owner.

## 6. Why this is not a reduction of the ownership standard

The original gate tested a platform representation that does not exist for Part
Feature Pattern copies. Keeping that gate would test API object-model shape, not
whether an instance is exactly and reproducibly attributable.

The proposal preserves the engineering standard:

- identity must be exact and unique;
- evidence must come from native API objects and persistent B-Rep entities;
- the full relation must survive save/reopen;
- ambiguity remains a failure;
- no matcher threshold or golden result changes;
- a weaker `PATTERN_ONLY` result remains non-acceptable.

The revised contract therefore changes the **permitted proof form** for one
explicit CAD domain; it does not accept weaker or ambiguous proof.

## 7. Effect on B001–B005

No effect is proposed.

- B001–B005 remain frozen within their defined scopes.
- Their golden data, evidence, thresholds, and ownership classifications are not
  reinterpreted.
- Direct feature ownership that is currently required as `API_EXACT` remains
  required as `API_EXACT`.
- `INSTANCE_EXACT` is not retroactively introduced into ordinary Base, Hole,
  Slot, Boss, or multi-feature validation.
- This proposal cannot convert an existing B001–B005 failure into a pass.

The proposed exception is scoped exclusively to generated occurrences of a
native SolidWorks Part Feature Pattern for which no occurrence object exists.

## 8. Future Assembly Pattern extension

Assembly patterns must use a separate ownership domain, for example:

```text
ownership_domain = ASSEMBLY_COMPONENT_PATTERN
```

SolidWorks assembly instances are represented by `IComponent2` objects and can
have component IDs and persistent references. Therefore the expected future
Assembly Pattern gate should remain:

```text
component occurrence ownership == API_EXACT
```

The Part Pattern exception must not automatically permit `INSTANCE_EXACT` for an
Assembly Pattern when a direct component occurrence object is available.

Suggested future domain expectations:

| Domain | Expected highest level | Default acceptance |
|---|---|---|
| `PART_FEATURE_PATTERN` | `INSTANCE_EXACT` for copies; `API_EXACT` for seed | Accept exact mixed chain under section 5 |
| `PART_BODY_PATTERN` | Potential `API_EXACT` body identity | Require separate capability validation |
| `ASSEMBLY_COMPONENT_PATTERN` | `API_EXACT` component occurrence | Require `API_EXACT` |
| Other CAD backend | Backend-specific | No inheritance without capability evidence |

This separation leaves room for stronger future APIs without weakening their
acceptance requirements.

## 9. Risks and controls

| Risk | Required control |
|---|---|
| Topology changes invalidate a generated face | Persistent-reference restore and complete save/reopen revalidation |
| Pattern edit changes instance numbering | Re-read count, skipped state, index, and transform; never trust stored index alone |
| Two instances have indistinguishable evidence | Reject unique attribution; return `PATTERN_ONLY` or `OWNERSHIP_UNRESOLVED` |
| Configuration changes occurrence layout | Include configuration identity in the evidence scope |
| Drawing hides multiple instances on one support | Preserve `ownership_set`; do not force one owner |
| Policy leaks into Assembly Pattern | Require an explicit ownership-domain discriminator |
| Reports obscure mixed evidence strength | Report exact counts for all four levels and keep strict labels |

## 10. Approval and transition conditions

Approval of this proposal should authorize only a later contract/documentation
change. It must not itself declare B006 accepted.

Before B006 can move from `NOT VALIDATED`, a separate implementation/review task
must confirm that:

1. the approved wording is represented without modifying golden geometry;
2. all mandatory `INSTANCE_EXACT` evidence fields are present;
3. all negative tests still fail for the intended reasons;
4. B001–B005 regression remains unchanged;
5. the real SolidWorks save/reopen evidence is rerun or formally accepted as the
   evidence baseline;
6. the final report shows the mixed result explicitly rather than reporting all
   occurrences as `API_EXACT`.

## 11. Proposed decision

**Proposed:** approve a domain-specific revision of the B006 acceptance contract.

Accept the following as an exact Part Feature Pattern ownership chain:

```text
Seed: API_EXACT
Generated copies: INSTANCE_EXACT or API_EXACT
PATTERN_ONLY: 0
OWNERSHIP_UNRESOLVED: 0
UNKNOWN: 0
UNATTRIBUTED: 0
```

All other B006 gates remain mandatory. B001–B005 remain unchanged. Future
Assembly Component Pattern validation must use its own domain and should require
`API_EXACT` whenever SolidWorks exposes direct `IComponent2` occurrence identity.

Until explicit approval and a subsequent validation review, the authoritative
status remains:

```text
B006 NOT VALIDATED
```
