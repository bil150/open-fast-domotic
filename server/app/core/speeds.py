"""The three speeds of a fade. They are the only ones: a glide too short for the radio to follow makes the
lights stutter, so the scenes cannot be given any other time."""

from typing import Literal

Speed = Literal["fast", "medium", "slow"]

# Seconds a light takes to glide to a color, and, in an animated scene, the time each color lasts:
# the lights then glide all the time, they never stop on a color and jump to the next.
SPEED_SECONDS: dict[Speed, float] = {"fast": 2.0, "medium": 6.0, "slow": 15.0}

# No glide is ever shorter: with 1.5 s or less the commands of several lights do not reach them in time.
MIN_GLIDE = SPEED_SECONDS["fast"]


def nearest_speed(seconds: float) -> Speed:
    """The speed closest to a time, for the scenes saved before there were three speeds."""
    return min(SPEED_SECONDS, key=lambda name: abs(SPEED_SECONDS[name] - seconds))
