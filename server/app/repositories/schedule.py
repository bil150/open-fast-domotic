from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Schedule]:
        return list(await self.session.scalars(select(Schedule).order_by(Schedule.id)))

    async def get(self, schedule_id: int) -> Schedule | None:
        return await self.session.get(Schedule, schedule_id)

    async def add(self, **fields: Any) -> Schedule:
        schedule = Schedule(**fields)
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def delete(self, schedule: Schedule) -> None:
        await self.session.delete(schedule)
