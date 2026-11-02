from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.speeds import SPEED_SECONDS, Speed, nearest_speed
from app.core.types import Json

from .light import LightRequest


class SceneAction(LightRequest):
    """The state one device must reach when the scene is applied."""

    device_id: str


class SceneTarget(BaseModel):
    type: Literal["room", "group"]
    id: int


class PaletteColor(BaseModel):
    """One color of a scene: a color or a white, with an optional brightness."""

    model_config = ConfigDict(extra="forbid")

    hex_color: str | None = Field(None, pattern=r"^#?[0-9a-fA-F]{6}$")
    color_temp_kelvin: int | None = Field(None, ge=1000, le=10000, description="white light")
    brightness: int | None = Field(None, ge=0, le=255)

    @model_validator(mode="after")
    def _one_color(self) -> "PaletteColor":
        if (self.hex_color is None) == (self.color_temp_kelvin is None):
            raise ValueError("give either hex_color or color_temp_kelvin")
        return self


class SceneIn(BaseModel):
    """Either `actions` (one state per device) or `target` + `palette` (a room or group, colored)."""

    name: str = Field(..., min_length=1, max_length=60)
    actions: list[SceneAction] = Field(default_factory=list)
    target: SceneTarget | None = None
    palette: list[PaletteColor] = Field(default_factory=list, max_length=16)
    assignments: dict[str, int] = Field(default_factory=dict, description="device id -> palette index")
    switches: dict[str, bool] = Field(
        default_factory=dict,
        description="device id -> on/off, for the sockets and the lights that must be off. "
        "A socket that is not listed is left as it is",
    )
    speed: Speed = Field(
        "medium",
        description="how long the lights take to glide to their color: fast (2 s), medium (6 s) or slow (15 s). "
        "In an animated scene each color lasts that long and the lights glide all the time",
    )
    animated: bool = Field(False, description="the lights step through the palette in a loop")

    @property
    def fade_seconds(self) -> float:
        """The glide of a scene made of a palette (the older scenes keep the time of each action)."""
        return SPEED_SECONDS[self.speed] if self.target else 0.0

    @model_validator(mode="after")
    def _check_shape(self) -> "SceneIn":
        if self.animated:
            if self.target is None or len(self.palette) < 2:
                raise ValueError("an animated scene needs a target and at least two colors")
            # one brightness for the whole palette: a change of brightness while the color glides makes
            # many bulbs stutter or skip the glide. The first color sets it.
            for color in self.palette[1:]:
                color.brightness = self.palette[0].brightness
        if self.target is None:
            if not self.actions:
                raise ValueError("give actions, or a target with a palette")
            if self.palette or self.assignments or self.switches:
                raise ValueError("a palette needs a target")
            return self
        if self.actions:
            raise ValueError("a scene has either actions or a target, not both")
        if not self.palette:
            raise ValueError("a target needs at least one color")
        if any(not 0 <= index < len(self.palette) for index in self.assignments.values()):
            raise ValueError("assignments must point to a color of the palette")
        return self


class SceneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    actions: list[Json]
    target: Json | None = None
    palette: list[Json] = []
    assignments: dict[str, int] = {}
    switches: dict[str, bool] = {}
    speed: Speed | None = None
    fade: float = 0
    animated: bool = False
    duration: float = 5
    running: bool = False

    @model_validator(mode="after")
    def _speed_of_older_scenes(self) -> "SceneOut":
        if self.speed is None and self.target is not None:
            self.speed = nearest_speed(self.duration if self.animated else self.fade)
        return self

    @field_validator("palette", "assignments", "switches", "fade", mode="before")
    @classmethod
    def _none_is_empty(cls, value: Any, info: Any) -> Any:
        if value is None:
            if info.field_name == "fade":
                return 0
            return [] if info.field_name == "palette" else {}
        return value


class SceneApplyOut(BaseModel):
    results: dict[str, bool] = Field(..., description="device id -> did it acknowledge")
