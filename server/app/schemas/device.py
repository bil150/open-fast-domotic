from typing import Any

from pydantic import BaseModel, Field


class ButtonEventState(BaseModel):
    event: str
    at: str


class DeviceState(BaseModel):
    power: bool | None = None
    brightness: int | None = None
    hue: float | None = None
    saturation: float | None = None
    hex_color: str | None = None
    color_temp_kelvin: int | None = None
    temperature: float | None = Field(None, description="degrees Celsius")
    battery: int | None = Field(None, description="percent")
    last_button: ButtonEventState | None = None


class DeviceOut(BaseModel):
    id: str
    protocol: str
    name: str
    model: str
    manufacturer: str
    type: str
    capabilities: list[str]
    online: bool | None = Field(None, description="None until the device was contacted")
    nwk: str | None = None
    last_seen: str | None = None
    lqi: int | None = None
    rssi: int | None = None
    state: DeviceState = DeviceState()
    color_temp_range_kelvin: list[int] | None = None
    endpoints: dict[str, Any] | None = None


class DeviceRename(BaseModel):
    name: str | None = Field(None, max_length=60, description="empty/null restores the default name")


class DevicesOut(BaseModel):
    devices: list[DeviceOut]


class CoordinatorOut(BaseModel):
    coordinators: list[dict[str, Any]]


class MessageOut(BaseModel):
    info: str
