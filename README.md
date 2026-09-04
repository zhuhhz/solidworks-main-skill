# solidworks-main-skill

`solidworks-main-skill` is an engineering-reasoning Skill for deterministic mechanical reconstruction and drawing delivery.

It owns the engineering layer:

- Three Views -> Projection Graph -> Feature Hypothesis -> Feature Graph -> Modeling Plan
- 3D model -> Drawing Plan -> View/Dimension/Section planning -> Drawing QA
- B-Rep, projection, and round-trip validation

It does **not** own or vendor the SolidWorks COM execution layer. The third-party project [`wzyn20051216/solidworks-automation-skill`](https://github.com/wzyn20051216/solidworks-automation-skill) is an external SolidWorks automation backend and technical reference. Integration must use an adapter, import, wrapper, or CLI/subprocess boundary.

See [architecture](docs/architecture.md), [upstream integration](docs/upstream_integration.md), and the [Benchmark 001 report](experiments/three_view_reconstruction/THREE_VIEW_RECONSTRUCTION_REPORT.md).

## Testing

Use `python -m pytest` as the canonical test entrypoint on this Windows environment. Do not assume `pytest.exe` is available on `PATH`. See [testing instructions](docs/testing.md) for file, test-node, verbosity, and live-output examples.

## Status

Benchmarks 001 and 002 pass deterministic input consistency, feature inference, native SolidWorks creation, B-Rep/Feature Tree validation, Level 1 structured projection, Level 2A vector geometry, and Level 2B drawing semantics on SolidWorks 2024 SP04. B002's former v0.2 reference was proven `REFERENCE_INVALID` through exact projected-edge topology, archived, and corrected without relaxing matcher thresholds. See the [progress report](docs/PROJECT_PROGRESS_REPORT.md) and [B002 reference audit](docs/B002_REFERENCE_AUDIT.md).

## Transitional note

This local repository was initially created from a full upstream working copy before the project boundary was established. Those copied upstream directories are a temporary migration artifact, not `solidworks-main-skill` source. No new core logic may be placed in them; the next cleanup must remove them from this repository after preserving only this project's own artifacts and documents.
