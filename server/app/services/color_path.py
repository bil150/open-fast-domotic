"""The path of a light between two colors of an animated scene.

Left to itself a bulb goes from a color to the next one in a straight line through its color space.
From a deep blue to a pale color that makes the perceived brightness jump (blue is very dark to the eye,
a pale color is not) and cuts through washed-out colors: a visible shortcut. Here the way is cut in a few
steps whose hue turns the short way round and whose saturation changes evenly, so the change is
gentle and never cuts through washed-out colors. The brightness is the same all along (see below).

A bulb that does color only receives a hue and a saturation (its value is dropped) and a level, so
a point is worked out in those terms. The level never changes on the way. Pure functions, no radio here.
"""

import colorsys
import math

from app.core.speeds import MIN_GLIDE
from app.core.types import Json

MAX_LEVEL = 254  # 255 is "invalid" in ZCL
MIN_SEGMENT = MIN_GLIDE  # seconds: below it the radio cannot follow a series of short glides
MAX_SEGMENTS = 4  # a few commands per color and per light, the radio is shared
HUE_PER_SEGMENT = 45.0  # degrees of hue (at full saturation) one segment may cover
LIGHTNESS_PER_SEGMENT = 20.0  # perceived brightness (L*, 0-100) one segment may change
GREY = 0.05  # below this saturation the hue means nothing: it follows the other color


# --- colors ---------------------------------------------------------------------
def kelvin_to_rgb(kelvin: float) -> tuple[float, float, float]:
    """Rough on-screen color of a white light (1000-10000 K), each channel 0-1."""
    t = max(1000.0, min(kelvin, 10000.0)) / 100
    red = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    green = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    blue = 255.0 if t >= 66 else 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    return tuple(max(0.0, min(255.0, v)) / 255 for v in (red, green, blue))  # type: ignore[return-value]


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16) / 255, int(value[2:4], 16) / 255, int(value[4:6], 16) / 255


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02x}" for v in rgb)


def kelvin_to_hex(kelvin: float) -> str:
    return _rgb_to_hex(kelvin_to_rgb(kelvin))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple[float, float, float]) -> float:
    """Relative luminance Y (0-1) of an sRGB color."""
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lightness(luminance: float) -> float:
    """Perceived lightness L* (0-100) of a luminance."""
    return 903.3 * luminance if luminance <= 0.008856 else 116 * luminance ** (1 / 3) - 16


class _Point:
    """A color as a bulb shows it: hue, saturation (value dropped) and the level it is lit at."""

    def __init__(self, color: Json) -> None:
        rgb = _hex_to_rgb(color["hex_color"]) if color.get("hex_color") else kelvin_to_rgb(color["color_temp_kelvin"])
        self.hue, self.saturation, _ = colorsys.rgb_to_hsv(*rgb)
        brightness = color.get("brightness")
        self.level = float(MAX_LEVEL if brightness is None else max(1, min(brightness, MAX_LEVEL)))
        self.lightness = _lightness(self.full_luminance(self.hue, self.saturation) * self.level / MAX_LEVEL)

    @staticmethod
    def full_luminance(hue: float, saturation: float) -> float:
        """Luminance of the color at full value, which is how the bulb shows it before its level."""
        return _luminance(colorsys.hsv_to_rgb(hue, saturation, 1.0))


def _hues(a: _Point, b: _Point) -> tuple[float, float]:
    """The two hues, a grey taking the hue of the other color so the hue does not sweep for nothing."""
    ha, hb = a.hue, b.hue
    if a.saturation < GREY:
        ha = hb
    if b.saturation < GREY:
        hb = ha
    return ha, hb


def _hue_arc(ha: float, hb: float) -> float:
    """Signed shortest way from ha to hb, as a fraction of the wheel (-0.5 to 0.5)."""
    return (hb - ha + 0.5) % 1.0 - 0.5


# --- the palette seen by one light ----------------------------------------------
def for_light(palette: list[Json], can_color: bool, can_white: bool) -> list[Json]:
    """The palette as this light can show it. A light that does color shows a white as a color when
    the palette has colors (or when it has no white of its own): it cannot glide between a color and
    a white temperature, it would jump."""
    has_color = any(c.get("hex_color") for c in palette)
    if not can_color or not (has_color or not can_white):
        return palette
    out: list[Json] = []
    for color in palette:
        if color.get("color_temp_kelvin"):
            converted: Json = {"hex_color": kelvin_to_hex(color["color_temp_kelvin"])}
            if color.get("brightness") is not None:
                converted["brightness"] = color["brightness"]
            out.append(converted)
        else:
            out.append(color)
    return out


def _both_white(a: Json, b: Json) -> bool:
    return bool(a.get("color_temp_kelvin")) and bool(b.get("color_temp_kelvin"))


# --- the way between two colors -------------------------------------------------
def segments(a: Json, b: Json, fade: float, can_color: bool) -> int:
    """How many steps the glide from `a` to `b` is cut in: as many as the change of hue and of perceived
    brightness need, as few as the radio allows. 1 means one plain glide."""
    if fade < 2 * MIN_SEGMENT or (not can_color and not _both_white(a, b)):
        return 1
    if _both_white(a, b):
        return 1  # a white temperature is already a straight way
    pa, pb = _Point(a), _Point(b)
    ha, hb = _hues(pa, pb)
    hue_degrees = abs(_hue_arc(ha, hb)) * 360 * max(pa.saturation, pb.saturation)
    needed = math.ceil(max(hue_degrees / HUE_PER_SEGMENT, abs(pb.lightness - pa.lightness) / LIGHTNESS_PER_SEGMENT, 1))
    return int(min(needed, MAX_SEGMENTS, fade // MIN_SEGMENT))


def waypoint(a: Json, b: Json, t: float, can_color: bool) -> Json:
    """The color a fraction `t` (0-1) of the way from `a` to `b`, as a palette color. At 1 it is
    exactly `b`. The level is that of `a`: the brightness of an animation does not change on the way
    (a level command sent during a color glide disturbs it on many bulbs)."""
    if t >= 1:
        return dict(b)
    if _both_white(a, b):
        mireds = (1 - t) * 1e6 / a["color_temp_kelvin"] + t * 1e6 / b["color_temp_kelvin"]
        out: Json = {"color_temp_kelvin": round(1e6 / mireds)}
        if a.get("brightness") is not None or b.get("brightness") is not None:
            la = MAX_LEVEL if a.get("brightness") is None else a["brightness"]
            lb = MAX_LEVEL if b.get("brightness") is None else b["brightness"]
            out["brightness"] = max(1, min(MAX_LEVEL, round((1 - t) * la + t * lb)))
        return out
    if not can_color:
        return dict(a)  # nothing but brightness to glide on such a light: it is done by the level of `a`/`b`
    pa, pb = _Point(a), _Point(b)
    ha, hb = _hues(pa, pb)
    hue = (ha + _hue_arc(ha, hb) * t) % 1.0
    saturation = (1 - t) * pa.saturation + t * pb.saturation
    point: Json = {"hex_color": _rgb_to_hex(colorsys.hsv_to_rgb(hue, saturation, 1.0))}
    if a.get("brightness") is not None:
        point["brightness"] = a["brightness"]
    return point
