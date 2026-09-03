# soildworks-main-skill

`soildworks-main-skill` is an engineering-reasoning Skill for deterministic mechanical reconstruction and drawing delivery.

It owns the engineering layer:

- Three Views -> Projection Graph -> Feature Hypothesis -> Feature Graph -> Modeling Plan
- 3D model -> Drawing Plan -> View/Dimension/Section planning -> Drawing QA
- B-Rep, projection, and round-trip validation

It does **not** own or vendor the SolidWorks COM execution layer. The third-party project [`wzyn20051216/solidworks-automation-skill`](https://github.com/wzyn20051216/solidworks-automation-skill) is an external SolidWorks automation backend and technical reference. Integration must use an adapter, import, wrapper, or CLI/subprocess boundary.

See [architecture](docs/architecture.md), [upstream integration](docs/upstream_integration.md), and the [Benchmark 001 report](experiments/three_view_reconstruction/THREE_VIEW_RECONSTRUCTION_REPORT.md).

## Status

Benchmarks 001 and 002 have passed deterministic input consistency, feature inference, native SolidWorks creation, B-Rep/Feature Tree validation, and Level 1 structured projection round-trip validation. Level 2 projected-vector extraction is experimental and currently reports `PARTIAL` because hidden-line semantics are not yet reliably exposed.

## Transitional note

This local repository was initially created from a full upstream working copy before the project boundary was established. Those copied upstream directories are a temporary migration artifact, not `soildworks-main-skill` source. No new core logic may be placed in them; the next cleanup must remove them from this repository after preserving only this project's own artifacts and documents.
