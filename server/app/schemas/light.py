from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.protocols.base import LightCommand


class LightRequest(BaseModel):
    """Change the state of a light: on/off, brightness, color or white."""

    model_config = ConfigDict(extra="forbid")

    power: bool | None = None
    brightness: int | None = Field(None, ge=0, le=255)
    hue: float | None = Field(None, ge=0, le=360, description="degrees, with saturation")
    saturation: float | None = Field(None, ge=0, le=100, description="percent, with hue")
    hex_color: str | None = Field(None, pattern=r"^#?[0-9a-fA-F]{6}$")
    color_temp_kelvin: int | None = Field(None, ge=1000, le=10000, description="white light")
    transition_time: float = Field(0, ge=0, le=600, description="seconds")

    @model_validator(mode="after")
    def _check_combination(self) -> "LightRequest":
        if (self.hue is None) != (self.saturation is None):
            raise ValueError("hue and saturation must be given together")
        colors = [self.hex_color is not None, self.hue is not None, self.color_temp_kelvin is not None]
        if sum(colors) > 1:
            raise ValueError("choose one of: hex_color, hue + saturation, color_temp_kelvin")
        if all(v is None for v in (self.power, self.brightness, self.hue, self.hex_color, self.color_temp_kelvin)):
            raise ValueError("nothing to change")
        return self

    def to_command(self) -> LightCommand:
        return LightCommand(
            power=self.power,
            brightness=self.brightness,
            hue=self.hue,
            saturation=self.saturation,
            hex_color=self.hex_color,
            color_temp_kelvin=self.color_temp_kelvin,
            transition_time=self.transition_time,
        )
