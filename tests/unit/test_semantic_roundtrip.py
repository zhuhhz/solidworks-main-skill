import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from drawing.drawing_semantic_extractor import extract
from validation.roundtrip_levels import split


def projected():
    return {"views": [{"name": "View1", "semantic_view": "front", "orientation": {},
                       "visible_segments": [{"x1": 0, "y1": 0, "x2": 10, "y2": 0}], "circles": []}]}


def semantic_evidence():
    line = {"x1": 0, "y1": 0, "x2": 10, "y2": 0}
    return {"status": "PASS", "hlr": {"post_reopen": [{"lines": [line], "circles": []}]},
            "differential": {"semantic_provenance": "HLV_MINUS_HLR", "views": [{"hidden_supports": [], "hidden_circles": []}]}}


def expected_graph(centerline_count=0, center_requirements=None):
    view = lambda count: SimpleNamespace(centerlines=[object()] * count)
    return SimpleNamespace(front=view(centerline_count), top=view(0), left=view(0), center_requirements=center_requirements or [])


def level_2_geometry():
    passing = {"visible_lines": {"status": "PASS"}, "circles": {"status": "PASS"}}
    return {"views": {"front": passing}}


def test_unknown_geometry_prevents_semantic_pass():
    graph = extract(projected())
    assert graph["status"] == "PARTIAL"
    assert graph["unknown_projected_primitive_count"] == 1
    assert split(level_2_geometry(), graph, expected_graph())["level_2b_drawing_semantics"]["status"] == "PARTIAL"


def test_hlv_minus_hlr_provenance_allows_semantic_pass_without_missing_centerlines():
    graph = extract(projected(), {}, semantic_evidence())
    result = split(level_2_geometry(), graph, expected_graph())["level_2b_drawing_semantics"]
    assert graph["views"][0]["projected_geometry"]["visible"][0]["source"] == "HLR_CAPTURE"
    assert result["status"] == "PASS"
    assert result["semantic_provenance"] == "HLV_MINUS_HLR"


def test_expected_centerline_without_annotation_keeps_level_2b_partial():
    graph = extract(projected(), {}, semantic_evidence())
    result = split(level_2_geometry(), graph, expected_graph(2))["level_2b_drawing_semantics"]
    assert result["status"] == "PARTIAL"
    assert result["reasons"] == ["EXPECTED_CENTERLINE_ANNOTATIONS_MISSING"]


def test_centermark_requirement_is_distinct_from_centerline():
    structure = {"professional_annotations": {"center_marks": [{"semantic_view": "front"}], "center_lines": []}}
    graph = extract(projected(), structure, semantic_evidence())
    expected = expected_graph(center_requirements=[{"kind": "CENTERMARK", "view": "front", "count": 1}])
    result = split(level_2_geometry(), graph, expected)["level_2b_drawing_semantics"]
    assert result["status"] == "PASS"
    assert result["expected_center_marks"] == 1
    assert result["expected_center_lines"] == 0


def test_missing_centermark_does_not_pass_as_centerline_or_axis():
    graph = extract(projected(), {}, semantic_evidence())
    expected = expected_graph(center_requirements=[{"kind": "CENTERMARK", "view": "front", "count": 1}])
    result = split(level_2_geometry(), graph, expected)["level_2b_drawing_semantics"]
    assert result["status"] == "PARTIAL"
    assert result["reasons"] == ["EXPECTED_CENTERMARK_ANNOTATIONS_MISSING"]
