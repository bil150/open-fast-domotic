from pydantic import BaseModel, Field, field_validator

from app.utils.cron import is_valid_cron


class ScheduleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    cron: str = Field(..., description="5 fields: minute hour day-of-month month day-of-week")
    scene_id: int
    enabled: bool = True

    @field_validator("cron")
    @classmethod
    def _valid_cron(cls, value: str) -> str:
        value = " ".join(value.split())
        if not is_valid_cron(value):
            raise ValueError("invalid cron expression (expected 5 fields, e.g. '30 7 * * 1-5')")
        return value


class ScheduleOut(BaseModel):
    id: int
    name: str
    cron: str
    scene_id: int
    enabled: bool
    last_run: str | None = None
    next_run: str | None = None
