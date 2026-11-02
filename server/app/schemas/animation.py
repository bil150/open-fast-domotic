from typing import Literal

from pydantic import BaseModel, Field


class AnimationKey(BaseModel):
    hue: float = Field(..., ge=0, le=360)
    saturation: float = Field(..., ge=0, le=100)
    brightness: int = Field(..., ge=0, le=255)
    transition_time: int = Field(..., ge=1, le=3600, description="seconds spent on this key")


class EffectIn(BaseModel):
    effect: Literal["fire", "candle"]
    brightness: int = Field(255, ge=1, le=255, description="the brightest the light gets")


class EffectOut(BaseModel):
    effect: Literal["fire", "candle"] | None = Field(..., description="None when no effect is running")


class AnimationIn(BaseModel):
    keys: list[AnimationKey] = Field(..., min_length=1, max_length=50)
