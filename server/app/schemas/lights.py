from pydantic import BaseModel, Field, model_validator


class LightsIn(BaseModel):
    """One order for many lights at once (a room, a group, the whole home)."""

    power: bool | None = Field(None, description="switch on or off every light and socket")
    brightness: int | None = Field(None, ge=1, le=255, description="set this brightness on the lights that dim")
    brightness_step: int | None = Field(
        None, ge=-100, le=100, description="percent to add (or remove, if negative) to each light's brightness"
    )
    transition_time: float = Field(0.5, ge=0, le=600, description="seconds")

    @model_validator(mode="after")
    def _check(self) -> "LightsIn":
        if self.power is None and self.brightness is None and self.brightness_step is None:
            raise ValueError("nothing to change")
        if self.brightness is not None and self.brightness_step is not None:
            raise ValueError("give either brightness or brightness_step")
        return self


class StreamIn(BaseModel):
    """One message of the /stream WebSocket: the newest brightness and color of a light."""

    device_id: str
    brightness: int | None = Field(None, ge=0, le=255, strict=True)
    hex_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class LightsOut(BaseModel):
    results: dict[str, bool] = Field(..., description="device id -> did it acknowledge")
