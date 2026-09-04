# Upstream migration test boundary

`solidworks-main-skill` retains a temporary copied compatibility tree from the
third-party `wzyn20051216/solidworks-automation-skill`, but does not claim all
of that project's workstation or packaging contracts.

Two exact node IDs are marked `upstream_compat` during collection:

- `tests/test_cad_reliability.py::test_discover_installation_supports_injected_filesystem`
- `tests/test_release_check.py::test_release_check_passes_current_tree`

The first assumes an upstream AutoCAD discovery candidate at a fixed path. The
second requires the upstream desktop application's bundled-skill snapshot at
`apps/workbench-ui/src-tauri/resources/skill`. Neither path is a promised
artifact of this engineering-reasoning project. Creating fake paths would hide
the migration boundary instead of testing it.

The main release gate remains:

```powershell
python -m pytest
```

The retained migration contracts can still be audited explicitly:

```powershell
python -m pytest -m upstream_compat -v --tb=long
```

They are deselected, not deleted and not marked skip. All other tests in the
same files remain in the normal test run. The marker must be removed from each
node only when its underlying capability or release artifact becomes an
explicit `solidworks-main-skill` commitment.
