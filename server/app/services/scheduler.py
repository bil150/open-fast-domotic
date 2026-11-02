"""Server-side cron: every minute, the schedules whose expression matches apply
their scene. Times are in the server's local timezone (set TZ in Docker)."""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import datetime

from app.utils.cron import matches

from .scenes import SceneService
from .schedules import ScheduleService

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        schedules: ScheduleService,
        scenes: SceneService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._schedules = schedules
        self._scenes = scenes
        self._clock = clock
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            now = self._clock()
            # wake up just after the next minute boundary
            await asyncio.sleep(60.5 - now.second - now.microsecond / 1_000_000)
            try:
                await self.tick(self._clock())
            except Exception:
                logger.exception("Scheduler tick failed")

    async def tick(self, now: datetime) -> list[int]:
        """Run the schedules matching this minute. Returns their ids."""
        minute = now.replace(second=0, microsecond=0)
        due = await self._schedules.claim_due(minute.isoformat(timespec="minutes"), lambda cron: matches(cron, minute))
        for schedule in due:
            logger.info("Schedule '%s' fired (scene %s)", schedule.name, schedule.scene_id)
            try:
                await self._scenes.apply(schedule.scene_id)
            except Exception:
                logger.exception("Schedule '%s' failed", schedule.name)
        return [s.id for s in due]
