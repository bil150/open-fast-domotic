from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.session import SessionFactory
from app.models import Schedule
from app.repositories import SceneRepository, ScheduleRepository
from app.schemas.schedule import ScheduleIn, ScheduleOut
from app.utils.cron import next_run


def _out(schedule: Schedule) -> ScheduleOut:
    return ScheduleOut(
        id=schedule.id,
        name=schedule.name,
        cron=schedule.cron,
        scene_id=schedule.scene_id,
        enabled=schedule.enabled,
        last_run=schedule.last_run,
        next_run=next_run(schedule.cron) if schedule.enabled else None,
    )


class ScheduleService:
    """CRUD of the cron schedules. The Scheduler is what runs them."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def _check_scene(self, session: AsyncSession, scene_id: int) -> None:
        if await SceneRepository(session).get(scene_id) is None:
            raise NotFoundError(f"Unknown scene {scene_id}")

    async def list_all(self) -> list[ScheduleOut]:
        async with self._sessions() as session:
            return [_out(s) for s in await ScheduleRepository(session).list_all()]

    async def get(self, schedule_id: int) -> ScheduleOut:
        async with self._sessions() as session:
            schedule = await ScheduleRepository(session).get(schedule_id)
            if schedule is None:
                raise NotFoundError(f"Unknown schedule {schedule_id}")
            return _out(schedule)

    async def create(self, data: ScheduleIn) -> ScheduleOut:
        async with self._sessions() as session:
            await self._check_scene(session, data.scene_id)
            schedule = await ScheduleRepository(session).add(**data.model_dump())
            await session.commit()
            return _out(schedule)

    async def update(self, schedule_id: int, data: ScheduleIn) -> ScheduleOut:
        async with self._sessions() as session:
            schedule = await ScheduleRepository(session).get(schedule_id)
            if schedule is None:
                raise NotFoundError(f"Unknown schedule {schedule_id}")
            await self._check_scene(session, data.scene_id)
            for field, value in data.model_dump().items():
                setattr(schedule, field, value)
            await session.commit()
            return _out(schedule)

    async def delete(self, schedule_id: int) -> None:
        async with self._sessions() as session:
            repository = ScheduleRepository(session)
            schedule = await repository.get(schedule_id)
            if schedule is None:
                raise NotFoundError(f"Unknown schedule {schedule_id}")
            await repository.delete(schedule)
            await session.commit()

    async def claim_due(self, minute_key: str, is_due: Callable[[str], bool]) -> list[Schedule]:
        """Return the enabled schedules for which `is_due(cron)` holds, and that
        did not already run this minute; mark them as run."""
        due: list[Schedule] = []
        async with self._sessions() as session:
            for schedule in await ScheduleRepository(session).list_all():
                if schedule.enabled and schedule.last_run != minute_key and is_due(schedule.cron):
                    schedule.last_run = minute_key
                    due.append(schedule)
            await session.commit()
        return due
