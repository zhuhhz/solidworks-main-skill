---
name: solidworks-main-skill
description: Reconstruct simple mechanical parts from structured orthographic views and plan validated 3D-to-drawing workflows. Use for Projection Graphs, Feature Graphs, Modeling Plans, Drawing Plans, and round-trip validation; use an external SolidWorks automation backend only through this project's adapter boundary.
---

# solidworks-main-skill

## Ownership boundary

This Skill is the engineering-reasoning layer. It owns projection understanding, feature hypotheses, reconstruction/drawing plans, and validation. It must not describe the third-party `wzyn20051216/solidworks-automation-skill` as this project or as an owned Skill.

Treat that repository only as an **external SolidWorks automation backend**. Do not copy its broad source tree. Use a dependency, configured checkout, adapter, import, or CLI/subprocess integration. Record a missing required external capability as `UPSTREAM_GAP` before adding a minimal local supplement.

## Reconstruction workflow

For standard, unambiguous orthographic inputs:

1. Parse into a Projection Graph; keep projection-coordinate mapping in one module.
2. Run consistency checks. Return `INPUT_INCONSISTENT` before backend execution on conflicting dimensions.
3. Produce auditable Feature Hypotheses. Return `AMBIGUOUS` rather than guessing when evidence cannot distinguish a hole, boss, or recess.
4. Convert confirmed features into a backend-neutral Modeling Plan.
5. Execute only through `backends/solidworks_automation`.
6. Validate saved/reopened model geometry, Feature Tree, and B-Rep.
7. Regenerate standard views and perform the highest available round-trip comparison level. State limitations precisely.

## Drawing workflow

Keep Drawing Plan, layout, dimension/annotation planning, section handling, and drawing QA independent of the backend. A non-overlapping, manufacturable drawing requires a final validation gate; a successful API return is insufficient.

Read [docs/upstream_integration.md](docs/upstream_integration.md) before changing the backend adapter. Read [docs/benchmark_spec.md](docs/benchmark_spec.md) when adding or running a benchmark.
