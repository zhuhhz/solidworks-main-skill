import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from validation.primitive_matcher import match_line_supports


def line(x1, y1, x2, y2):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def test_split_segments_have_equivalent_support():
    result = match_line_supports([line(0, 0, 100, 0)], [line(0, 0, 40, 0), line(40, 0, 100, 0)])
    assert result["status"] == "PASS"
    assert result["support_iou"] == 1.0
    assert result["segmentation"] == "SEGMENTATION_DIFFERENT"
    assert result["information"] == ["GEOMETRY_EQUIVALENT", "SEGMENTATION_DIFFERENT"]


def test_vertical_lines_use_normal_form_without_slope_special_case():
    result = match_line_supports([line(12, 0, 12, 80)], [line(12.04, 0, 12.04, 80)])
    assert result["status"] == "PASS"


def test_critical_internal_gap_is_not_hidden_by_high_total_coverage():
    result = match_line_supports([line(0, 0, 100, 0)], [line(0, 0, 49, 0), line(51, 0, 100, 0)])
    assert result["status"] == "FAIL"
    assert result["max_gap_mm"] == 2.0


def test_overflow_is_reported_and_rejected():
    result = match_line_supports([line(0, 0, 100, 0)], [line(-5, 0, 105, 0)])
    assert result["status"] == "FAIL"
    assert result["overflow_length_mm"] == 10.0


def test_small_angular_noise_clusters_on_same_support():
    result = match_line_supports([line(0, 0, 100, 0)], [line(0, 0.02, 100, 0.03)])
    assert result["status"] == "PASS"
