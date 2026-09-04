import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = PROJECT_ROOT / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(EXPERIMENT_ROOT))

from parser.structured_input import load_structured_input
from validation.projection_support_tracer import _on_support


def _supports(segments, target):
    return any(_on_support(segment.__dict__, target) for segment in segments)


def test_b002_corrected_reference_contains_proven_baseblock_supports():
    graph = load_structured_input(EXPERIMENT_ROOT / "benchmarks" / "case_002_step_block.json")
    assert graph.reference_integrity["history_status"] == "REFERENCE_INVALID"
    assert _supports(graph.top.visible_segments, {"x1": 20, "y1": 20, "x2": 80, "y2": 20})
    assert _supports(graph.left.visible_segments, {"x1": 20, "y1": 10, "x2": 20, "y2": 50})


def test_b002_hole_center_contract_requires_centermark_not_centerline():
    graph = load_structured_input(EXPERIMENT_ROOT / "benchmarks" / "case_002_step_block.json")
    assert graph.front.centerlines == []
    assert graph.center_requirements == [{
        "view": "front", "target": "circle:0", "kind": "CENTERMARK",
        "purpose": "HOLE_CENTER_INDICATION", "count": 1,
    }]


def test_b002_invalid_reference_is_preserved_verbatim_as_schema_v02():
    archive = EXPERIMENT_ROOT / "benchmarks" / "archive" / "case_002_step_block.reference-invalid.v0.2.json"
    raw = json.loads(archive.read_text(encoding="utf-8"))
    assert raw["schema_version"] == "0.2"
    assert len(raw["front"]["centerlines"]) == 2
    assert not any(_on_support(line, {"x1": 20, "y1": 20, "x2": 80, "y2": 20}) for line in raw["top"]["visible_segments"])
