# External backend integration

The third-party `wzyn20051216/solidworks-automation-skill` is an upstream automation skill. It is not part of `soildworks-main-skill` and must not be represented as owned source.

The adapter accepts a configured external checkout through `SOLIDWORKS_AUTOMATION_BACKEND_PATH`. It may import documented modules or invoke a stable CLI entrypoint. Keep COM calls behind the adapter.

When a required operation is not available or cannot be validated in the upstream backend, return an `UPSTREAM_GAP` record containing the operation, observed limitation, version, and a proposed minimal local compatibility implementation. Do not silently use a replacement and claim upstream support.
