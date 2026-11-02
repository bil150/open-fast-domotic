import colorsys

import pytest

from app.services import color_path
from app.services.color_path import for_light, segments, waypoint


def hue_of(color: dict) -> float:
    value = color["hex_color"].lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


BLUE = {"hex_color": "#0000ff", "brightness": 254}
PALE = {"hex_color": "#ffffcc", "brightness": 254}


def test_the_end_of_the_way_is_exactly_the_color_asked():
    assert waypoint(BLUE, PALE, 1.0, True) == PALE


def test_the_level_never_changes_on_the_way():
    """A level command sent during a color glide disturbs it on many bulbs: only the color moves."""
    for t in (0.25, 0.5, 0.75):
        assert waypoint(BLUE, PALE, t, True)["brightness"] == 254
    no_level = waypoint({"hex_color": "#0000ff"}, {"hex_color": "#ffffcc"}, 0.5, True)
    assert "brightness" not in no_level


def test_the_hue_turns_the_short_way_round():
    red, violet = {"hex_color": "#ff0000"}, {"hex_color": "#8000ff"}  # hue 0 and 270
    middle = waypoint(red, violet, 0.5, True)
    assert hue_of(middle) == pytest.approx(315, abs=15)  # through magenta, not through green (135)


def test_a_grey_does_not_make_the_hue_sweep():
    white = {"hex_color": "#ffffff", "brightness": 254}
    for t in (0.25, 0.5, 0.75):
        assert hue_of(waypoint(BLUE, white, t, True)) == pytest.approx(240, abs=3)


def test_a_white_temperature_glides_in_mireds():
    warm, cold = {"color_temp_kelvin": 2200, "brightness": 100}, {"color_temp_kelvin": 6500, "brightness": 200}
    middle = waypoint(warm, cold, 0.5, True)
    assert middle["color_temp_kelvin"] == pytest.approx(3289, abs=5)  # the middle of 454 and 154 mireds
    assert middle["brightness"] == 150


def test_how_many_steps_a_glide_is_cut_in():
    assert segments(BLUE, PALE, 2.0, True) == 1  # too short for the radio to follow several commands
    assert 3 <= segments(BLUE, PALE, 8.0, True) <= color_path.MAX_SEGMENTS
    assert segments(BLUE, dict(BLUE), 8.0, True) == 1  # nothing changes
    assert segments(BLUE, PALE, 4.5, True) <= 3  # a step is never shorter than MIN_SEGMENT
    assert segments(BLUE, PALE, 8.0, False) == 1  # a bulb that does not do color has nothing to cut
    assert segments({"color_temp_kelvin": 2200}, {"color_temp_kelvin": 6500}, 8.0, True) == 1


def test_a_light_that_does_color_shows_the_whites_as_colors_when_the_palette_has_colors():
    palette = [{"hex_color": "#ff0000"}, {"color_temp_kelvin": 2700, "brightness": 100}]
    shown = for_light(palette, can_color=True, can_white=True)
    assert shown[0] == palette[0]
    assert shown[1]["hex_color"].startswith("#") and "color_temp_kelvin" not in shown[1]
    assert shown[1]["brightness"] == 100
    # it could not glide between a color and a white temperature, but a light without color has no choice
    assert for_light(palette, can_color=False, can_white=True) == palette


def test_a_palette_of_whites_stays_white_on_a_light_that_does_white():
    whites = [{"color_temp_kelvin": 2200}, {"color_temp_kelvin": 4000}]
    assert for_light(whites, can_color=True, can_white=True) == whites
    assert "hex_color" in for_light(whites, can_color=True, can_white=False)[0]  # no white of its own
