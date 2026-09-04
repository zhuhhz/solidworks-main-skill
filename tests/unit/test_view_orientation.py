import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))
from drawing.view_coordinate_transform import normalize_primitives, to_view_local_mm
from drawing.view_orientation import canonicalize, comparable, cross


def test_front_top_right_are_explicit_frames():
    assert canonicalize("*Front").normal == (0.0, 0.0, 1.0)
    assert canonicalize("Top").normal == (0.0, 1.0, 0.0)
    assert canonicalize("Right").normal == (1.0, 0.0, 0.0)
    for name in ("Front", "Top", "Right"):
        frame = canonicalize(name)
        assert frame.right == cross(frame.up, frame.normal)


def test_localized_solidworks_standard_view_names_are_supported():
    assert canonicalize("*前视").orientation.value == "FRONT"
    assert canonicalize("上视图").orientation.value == "TOP"


def test_left_and_right_are_not_name_equivalent():
    assert not comparable(canonicalize("Right"), canonicalize("Left"))


def test_sheet_position_and_scale_do_not_change_frame():
    plain = canonicalize("Front", "THIRD_ANGLE")
    solidworks_named = canonicalize("*Front", "THIRD_ANGLE")
    assert comparable(plain, solidworks_named)
    assert plain.projection_standard == solidworks_named.projection_standard


def test_sheet_translation_is_removed_from_view_local_geometry():
    base = [{"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 0.0}]
    moved = [{"x1": 23.0, "y1": 47.0, "x2": 123.0, "y2": 47.0}]
    assert normalize_primitives(base, [])[0] == normalize_primitives(moved, [])[0]


def test_model_geometry_is_scale_invariant_for_standard_view_scales():
    for scale in (1.0, 0.5, 2.0):
        assert to_view_local_mm((0.1, 0.06), scale=scale) == (100.0, 60.0)
