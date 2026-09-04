"""Main-project pytest collection boundary.

The repository temporarily retains selected tests copied with the external
backend migration.  They remain executable as ``upstream_compat`` evidence,
but are not part of the solidworks-main-skill release contract.
"""
from __future__ import annotations

import pytest


UPSTREAM_COMPAT_NODE_IDS = {
    "tests/test_cad_reliability.py::test_discover_installation_supports_injected_filesystem",
    "tests/test_release_check.py::test_release_check_passes_current_tree",
}


def pytest_collection_modifyitems(items):
    for item in items:
        if item.nodeid.replace("\\", "/") in UPSTREAM_COMPAT_NODE_IDS:
            item.add_marker(pytest.mark.upstream_compat)
