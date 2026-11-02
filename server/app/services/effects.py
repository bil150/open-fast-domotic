"""Light effects that never repeat: the next step is drawn at random (fireplace, candle)."""

import random
from typing import Literal, get_args

from app.protocols.base import LightCommand

Effect = Literal["fire", "candle"]
EFFECTS: tuple[str, ...] = get_args(Effect)

WARM_WHITE_KELVIN = 2000  # for bulbs that only do white


def next_step(effect: str, peak: int, rng: random.Random) -> tuple[LightCommand, float]:
    """The next light state of an effect and how long to wait before the one after.
    `peak` (1..255) is the brightest the light gets."""
    if effect == "fire":
        # logs burning: strong, quick and irregular changes between deep red and orange
        level = rng.uniform(0.35, 1.0)
        hue = rng.uniform(4, 28)
        saturation = rng.uniform(88, 100)
        transition = rng.uniform(0.1, 0.45)
        pause = rng.uniform(0.05, 0.3)
    elif effect == "candle":
        # a steady flame with small shivers, now and then a gust that makes it dip
        level = rng.uniform(0.15, 0.4) if rng.random() < 0.08 else rng.uniform(0.7, 1.0)
        hue = rng.uniform(24, 34)
        saturation = rng.uniform(85, 95)
        transition = rng.uniform(0.15, 0.4)
        pause = rng.uniform(0.05, 0.4)
    else:
        raise ValueError(f"Unknown effect {effect}")
    command = LightCommand(
        power=True,
        brightness=max(1, round(level * peak)),
        hue=hue,
        saturation=saturation,
        color_temp_kelvin=WARM_WHITE_KELVIN,
        transition_time=round(transition, 2),
    )
    return command, transition + pause
