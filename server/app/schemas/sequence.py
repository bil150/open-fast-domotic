from pydantic import BaseModel, ConfigDict, Field

from app.core.types import Json


class SequenceStep(BaseModel):
    scene_id: int
    duration: int = Field(..., ge=1, le=86400, description="seconds the scene is held before the next step")
    fade: bool = Field(True, description="glide to the scene, reaching it when the duration ends")


class SequenceIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    steps: list[SequenceStep] = Field(..., min_length=1, max_length=50)
    loop: bool = Field(True, description="start over after the last step; otherwise run once")
    enabled: bool = True


class SequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    steps: list[Json]
    loop: bool
    enabled: bool
    running: bool = False
