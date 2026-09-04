import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))

from drawing.view_orientation import canonicalize
from parser.projection_mapping import map_point_to_frame


def test_front_input_maps_directly_to_front_frame():
    assert map_point_to_frame("front", 25, 30, 100, 60, canonicalize("Front")) == (25.0, 30.0)


def test_top_positive_z_maps_to_solidworks_top_negative_z_screen_axis():
    assert map_point_to_frame("top", 25, 10, 100, 40, canonicalize("Top")) == (25.0, 30.0)


def test_left_positive_z_maps_to_generated_right_negative_z_screen_axis():
    assert map_point_to_frame("left", 10, 30, 40, 60, canonicalize("Right")) == (30.0, 30.0)
