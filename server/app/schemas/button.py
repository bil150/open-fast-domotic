from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Json


class RunScene(BaseModel):
    type: Literal["scene"]
    scene_id: int


class ToggleDevice(BaseModel):
    type: Literal["toggle"]
    device_id: str


class SetPower(BaseModel):
    type: Literal["power"]
    device_id: str
    state: bool


ButtonAction = Annotated[RunScene | ToggleDevice | SetPower, Field(discriminator="type")]


class ButtonMappingIn(BaseModel):
    device_id: str
    event: str = Field(..., min_length=1, description="e.g. on_off.toggle, see state.last_button")
    action: ButtonAction


class ButtonMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    event: str
    action: Json
