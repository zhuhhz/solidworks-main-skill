import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "experiments" / "three_view_reconstruction"
sys.path.insert(0, str(ROOT))
from drawing.view_orientation import canonicalize, comparable


def test_front_top_right_are_explicit_frames():
    assert canonicalize("*Front").view_normal_world == "+Z"
    assert canonicalize("Top").view_normal_world == "+Y"
    assert canonicalize("Right").view_normal_world == "+X"


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
