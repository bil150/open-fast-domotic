import asyncio
import contextlib
import logging
import random
from collections.abc import Coroutine
from typing import Any

from app.core.errors import DeviceNotFoundError
from app.db.session import SessionFactory
from app.protocols.base import LightCommand
from app.repositories import AnimationRepository
from app.schemas.animation import AnimationKey

from .effects import EFFECTS, next_step
from .hub import Hub

logger = logging.getLogger(__name__)

SOURCE = "animation"
UNKNOWN_DEVICE_RETRY = 30  # the radio may not be up yet when animations resume


class AnimationService:
    """Loops over color keys on a light. A direct command on the light stops it."""

    def __init__(self, sessions: SessionFactory, hub: Hub) -> None:
        self._sessions = sessions
        self._hub = hub
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._effects: dict[str, str] = {}  # device id -> name of the running effect
        hub.add_command_guard(self._on_command)

    async def _on_command(self, device_id: str, source: str) -> None:
        if source != SOURCE and device_id in self._tasks:
            logger.info("Animation of %s stopped by a manual command", device_id)
            await self.stop(device_id)

    def running(self) -> list[str]:
        return list(self._tasks)

    def effect_of(self, device_id: str) -> str | None:
        return self._effects.get(device_id)

    async def start(self, device_id: str, keys: list[AnimationKey], persist: bool = True) -> None:
        await self._launch(device_id, [k.model_dump() for k in keys], self._loop(device_id, keys), persist, None)

    async def start_effect(self, device_id: str, effect: str, peak: int = 255, persist: bool = True) -> None:
        """Random flicker (fireplace, candle) on a bulb, never the same twice. `peak` is its top brightness."""
        if effect not in EFFECTS:
            raise ValueError(f"Unknown effect {effect}")
        peak = max(1, min(peak, 255))
        await self._launch(
            device_id, [{"effect": effect, "peak": peak}], self._effect_loop(device_id, effect, peak), persist, effect
        )

    async def _launch(
        self,
        device_id: str,
        saved: list[dict[str, Any]],
        loop: Coroutine[Any, Any, None],
        persist: bool,
        effect: str | None,
    ) -> None:
        try:
            if persist:
                await self._hub.get_device(device_id)  # raises DeviceNotFoundError
            await self._cancel(device_id)
            if persist:
                async with self._sessions() as session:
                    await AnimationRepository(session).set(device_id, saved)
                    await session.commit()
        except BaseException:
            loop.close()  # never awaited: avoid the "coroutine was never awaited" warning
            raise
        self._tasks[device_id] = asyncio.ensure_future(loop)
        if effect:
            self._effects[device_id] = effect

    async def stop(self, device_id: str) -> bool:
        async with self._sessions() as session:
            await AnimationRepository(session).delete(device_id)
            await session.commit()
        return await self._cancel(device_id)

    async def restore(self) -> None:
        async with self._sessions() as session:
            saved = await AnimationRepository(session).get_all()
        for device_id, keys in saved.items():
            if keys and "effect" in keys[0]:
                await self.start_effect(device_id, keys[0]["effect"], keys[0].get("peak", 255), persist=False)
            else:
                await self.start(device_id, [AnimationKey(**k) for k in keys], persist=False)

    async def shutdown(self) -> None:
        for device_id in list(self._tasks):
            await self._cancel(device_id)

    async def _cancel(self, device_id: str) -> bool:
        self._effects.pop(device_id, None)
        task = self._tasks.pop(device_id, None)
        if task is None:
            return False
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return True

    async def _loop(self, device_id: str, keys: list[AnimationKey]) -> None:
        while True:
            for key in keys:
                command = LightCommand(
                    power=True,
                    hue=key.hue,
                    saturation=key.saturation,
                    brightness=key.brightness,
                    transition_time=key.transition_time,
                )
                try:
                    await self._hub.set_light(device_id, command, source=SOURCE)
                except DeviceNotFoundError:
                    await asyncio.sleep(UNKNOWN_DEVICE_RETRY)
                    continue
                except Exception:
                    logger.exception("Animation step failed on %s", device_id)
                await asyncio.sleep(key.transition_time)

    async def _effect_loop(self, device_id: str, effect: str, peak: int) -> None:
        rng = random.Random()
        while True:
            command, wait = next_step(effect, peak, rng)
            try:
                await self._hub.set_light(device_id, command, source=SOURCE)
            except DeviceNotFoundError:
                await asyncio.sleep(UNKNOWN_DEVICE_RETRY)
                continue
            except Exception:
                logger.exception("Effect step failed on %s", device_id)
            await asyncio.sleep(wait)
