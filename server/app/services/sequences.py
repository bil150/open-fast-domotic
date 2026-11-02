"""Sequences: scenes played one after the other, each held for its own duration
(scene A for 2 s, scene B for 5 s, scene C for 10 s...), optionally in a loop.
A sequence runs while it is enabled; disabling it stops it."""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.types import Json
from app.db.session import SessionFactory
from app.models import Sequence
from app.repositories import SceneRepository, SequenceRepository
from app.schemas.sequence import SequenceIn, SequenceOut

from .scenes import SceneService

logger = logging.getLogger(__name__)

# The next step is sent this many seconds before the current one is over: the command takes a moment
# to reach the light, and a fade that is restarted slightly early is smooth, whereas one that
# starts late leaves the light still for a moment.
LEAD = 0.1


class SequenceService:
    def __init__(
        self,
        sessions: SessionFactory,
        scenes: SceneService,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sessions = sessions
        self._scenes = scenes
        self._sleep = sleep
        self._clock = clock
        self._tasks: dict[int, asyncio.Task[None]] = {}

    def _out(self, sequence: Sequence) -> SequenceOut:
        task = self._tasks.get(sequence.id)
        out = SequenceOut.model_validate(sequence)
        out.running = task is not None and not task.done()
        return out

    async def _check_scenes(self, session: AsyncSession, data: SequenceIn) -> None:
        repository = SceneRepository(session)
        for step in data.steps:
            if await repository.get(step.scene_id) is None:
                raise NotFoundError(f"Unknown scene {step.scene_id}")

    async def list_all(self) -> list[SequenceOut]:
        async with self._sessions() as session:
            return [self._out(s) for s in await SequenceRepository(session).list_all()]

    async def get(self, sequence_id: int) -> SequenceOut:
        async with self._sessions() as session:
            sequence = await SequenceRepository(session).get(sequence_id)
            if sequence is None:
                raise NotFoundError(f"Unknown sequence {sequence_id}")
            return self._out(sequence)

    async def create(self, data: SequenceIn) -> SequenceOut:
        async with self._sessions() as session:
            await self._check_scenes(session, data)
            sequence = await SequenceRepository(session).add(
                name=data.name,
                steps=[s.model_dump() for s in data.steps],
                loop=data.loop,
                enabled=data.enabled,
            )
            await session.commit()
        self._sync(sequence)
        return self._out(sequence)

    async def update(self, sequence_id: int, data: SequenceIn) -> SequenceOut:
        async with self._sessions() as session:
            sequence = await SequenceRepository(session).get(sequence_id)
            if sequence is None:
                raise NotFoundError(f"Unknown sequence {sequence_id}")
            await self._check_scenes(session, data)
            sequence.name = data.name
            sequence.steps = [s.model_dump() for s in data.steps]
            sequence.loop = data.loop
            sequence.enabled = data.enabled
            await session.commit()
        await self._cancel(sequence_id)  # restart from the first step with the new steps
        self._sync(sequence)
        return self._out(sequence)

    async def delete(self, sequence_id: int) -> None:
        async with self._sessions() as session:
            repository = SequenceRepository(session)
            sequence = await repository.get(sequence_id)
            if sequence is None:
                raise NotFoundError(f"Unknown sequence {sequence_id}")
            await repository.delete(sequence)
            await session.commit()
        await self._cancel(sequence_id)

    async def restore(self) -> None:
        async with self._sessions() as session:
            for sequence in await SequenceRepository(session).list_all():
                self._sync(sequence)

    async def shutdown(self) -> None:
        for sequence_id in list(self._tasks):
            await self._cancel(sequence_id)

    def _sync(self, sequence: Sequence) -> None:
        """Start the sequence if it is enabled and not already running."""
        task = self._tasks.get(sequence.id)
        if sequence.enabled and (task is None or task.done()):
            self._tasks[sequence.id] = asyncio.ensure_future(self._run(sequence.id, sequence.steps, sequence.loop))

    async def _cancel(self, sequence_id: int) -> None:
        task = self._tasks.pop(sequence_id, None)
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _run(self, sequence_id: int, steps: list[Json], loop: bool) -> None:
        # Steps follow a timeline instead of "apply, then wait": the time a command takes to be
        # acknowledged does not add up, so a 2 s step really lasts 2 s.
        deadline = self._clock()
        while True:
            for step in steps:
                try:
                    fade = step["duration"] if step.get("fade", True) else None
                    await self._scenes.apply(step["scene_id"], fade)
                except NotFoundError:
                    logger.warning("Sequence %s: scene %s no longer exists", sequence_id, step["scene_id"])
                except Exception:
                    logger.exception("Sequence %s: step failed", sequence_id)
                deadline += step["duration"]
                now = self._clock()
                if deadline - LEAD < now:  # we fell behind (slow radio): resume from now, no burst
                    deadline = now + step["duration"]
                await self._sleep(deadline - LEAD - now)
            if not loop:
                break
        await self._finish(sequence_id)

    async def _finish(self, sequence_id: int) -> None:
        """A one-shot sequence is over: leave it disabled so it does not replay at startup."""
        async with self._sessions() as session:
            sequence = await SequenceRepository(session).get(sequence_id)
            if sequence is not None:
                sequence.enabled = False
                await session.commit()
