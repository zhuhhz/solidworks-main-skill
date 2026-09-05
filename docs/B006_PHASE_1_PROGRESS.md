# B006 Phase 1 — Pattern Feature Contract

Status: **B006 NOT VALIDATED**. Pure contract implementation only; no COM or real modeling.

Branch: `feat/benchmark-006-pattern`. Based on main following the local v0.5 baseline.

## Schema

`schemas/pattern_feature.py` adds SeedFeature, PatternFeature, InstanceFeature,
PatternFeatureGraph, PatternOperation and PatternOwnership. Existing B001–B005
classes and validators remain unchanged. feature_role identifies SEED/PATTERN/INSTANCE;
pattern_id records membership, source_feature_id records Base for Seed and Seed
for Pattern/Instances. instance_index is 0–3, with zero representing the seed occurrence.
The latest request's `seed_hole_001` / `instance_001`–004 IDs replace the planning
document's illustrative labels; IDs are independent of localized CAD names.

## Dependency and provenance

Required chain: Base → Seed → Pattern → Instances. Pattern membership on Seed
does not create a reverse dependency. Instances cannot depend directly on Base.
The operation contract is base_extrude → seed_hole_cut → linear_pattern. Every
instance traces to the shared pattern operation and its seed operation; instances
are not separate cuts. These are pure provenance descriptors, not executable CAD plans.

Instance enumeration order may yield ORDER_VARIANT_EQUIVALENT while stable indices
and identities are retained. Executing Pattern before Seed remains invalid: a
single dependency chain has no legal execution-order permutation.

## Geometry and ownership

The bounded B006 validator checks 100×60×20 Base, Ø10 seed at (-35,-10,0),
20 mm spacing along signed +X, four total occurrences including seed, and independent
per-index positions. It rejects consistent but wrong pitch/direction declarations.

As requested in Phase 1, API_EXACT and INSTANCE_EXACT may pass only with explicit
instance ID, native owner, identity reference, source and complete expected-entity
coverage. PATTERN_ONLY and OWNERSHIP_UNRESOLVED cannot pass. Unit fixtures test
these assertions; they do not prove that SolidWorks supplies such correspondence.
Shared projected support extraction and real per-instance ownership remain future work.

The slot-width UPSTREAM_GAP remains open. The third-party external backend is unchanged.

## Verification

Commands: `python -m pytest tests/unit/test_b006_pattern_contract.py -v` and
`python -m pytest -v`.

Results: 24 B006 tests passed; full suite 589 passed, 15 skipped, 2 deselected,
0 failed, 26 existing warnings, 22.18 seconds. No real SolidWorks validation
was performed. B006 remains NOT VALIDATED.
