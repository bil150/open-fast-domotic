from pydantic import BaseModel, ConfigDict, Field, field_validator


class ZoneIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    device_ids: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("device_ids")
    @classmethod
    def _unique(cls, ids: list[str]) -> list[str]:
        return list(dict.fromkeys(ids))


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    device_ids: list[str]
