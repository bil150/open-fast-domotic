"""The Hub owns the protocol coordinators. It is the only thing the rest of the
application talks to for anything related to devices, whatever their protocol."""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.errors import DeviceNotFoundError, UnsupportedCommandError
from app.core.types import Json
from app.db.session import SessionFactory
from app.protocols.base import BaseCoordinator, Capability, DeviceEvent, LightCommand
from app.repositories import DeviceNameRepository
from app.schemas.device import DeviceOut

logger = logging.getLogger(__name__)

EventHandler = Callable[[DeviceEvent], Awaitable[None] | None]
# called before a command is sent: (device_id, source). source is "user" or "animation"
CommandGuard = Callable[[str, str], Awaitable[None]]
# called once a device is removed, to forget everything kept about it: (device_id)
RemovalHandler = Callable[[str], Awaitable[None]]


class Hub:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions
        self.coordinators: list[BaseCoordinator] = []
        self._event_handlers: list[EventHandler] = []
        self._command_guards: list[CommandGuard] = []
        self._removal_handlers: list[RemovalHandler] = []
        self._ws_queues: set[asyncio.Queue[Json]] = set()

    # --- wiring -------------------------------------------------------------
    def register(self, coordinator: BaseCoordinator) -> None:
        coordinator.subscribe(self._on_event)
        self.coordinators.append(coordinator)

    def add_event_handler(self, handler: EventHandler) -> None:
        self._event_handlers.append(handler)

    def add_command_guard(self, guard: CommandGuard) -> None:
        self._command_guards.append(guard)

    def add_removal_handler(self, handler: RemovalHandler) -> None:
        self._removal_handlers.append(handler)

    # --- lifecycle ----------------------------------------------------------
    async def start(self) -> None:
        for coordinator in self.coordinators:
            try:
                await coordinator.start()
            except Exception:
                logger.exception("Could not start the %s coordinator", coordinator.protocol)

    async def stop(self) -> None:
        for coordinator in self.coordinators:
            try:
                await coordinator.stop()
            except Exception:
                logger.exception("Could not stop the %s coordinator", coordinator.protocol)

    def _coordinator_for(self, device_id: str) -> BaseCoordinator:
        for coordinator in self.coordinators:
            if coordinator.owns(device_id):
                return coordinator
        raise DeviceNotFoundError(f"Unknown device {device_id}")

    # --- devices ------------------------------------------------------------
    async def _names(self) -> dict[str, str]:
        async with self._sessions() as session:
            return await DeviceNameRepository(session).get_all()

    @staticmethod
    def _with_name(device: Json, names: dict[str, str]) -> DeviceOut:
        device["name"] = names.get(device["id"]) or device.get("name") or device["id"]
        return DeviceOut.model_validate(device)

    async def list_devices(self) -> list[DeviceOut]:
        names = await self._names()
        devices: list[DeviceOut] = []
        for coordinator in self.coordinators:
            devices.extend(self._with_name(d, names) for d in await coordinator.list_devices())
        return devices

    async def get_device(self, device_id: str) -> DeviceOut:
        device = await self._coordinator_for(device_id).get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Unknown device {device_id}")
        return self._with_name(device, await self._names())

    async def rename_device(self, device_id: str, name: str | None) -> DeviceOut:
        self._coordinator_for(device_id)
        async with self._sessions() as session:
            repository = DeviceNameRepository(session)
            if name and name.strip():
                await repository.set(device_id, name.strip())
            else:
                await repository.delete(device_id)
            await session.commit()
        return await self.get_device(device_id)

    async def remove_device(self, device_id: str) -> None:
        """Take the device off its network, then forget it everywhere (names, rooms, groups, scenes, buttons...).
        It also cleans what is left of a device the radio no longer knows, so it is never an error."""
        for coordinator in self.coordinators:
            if coordinator.owns(device_id):
                await coordinator.remove_device(device_id)
        for handler in self._removal_handlers:
            try:
                await handler(device_id)
            except Exception:
                logger.exception("Could not forget %s", device_id)

    async def refresh_device(self, device_id: str) -> DeviceOut:
        device = await self._coordinator_for(device_id).refresh(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Unknown device {device_id}")
        return self._with_name(device, await self._names())

    async def permit_join(self, seconds: int) -> None:
        for coordinator in self.coordinators:
            await coordinator.permit_join(seconds)

    def info(self) -> dict[str, Any]:
        return {"coordinators": [c.info() for c in self.coordinators]}

    # --- commands -----------------------------------------------------------
    async def _guard(self, device_id: str, source: str) -> None:
        for guard in self._command_guards:
            await guard(device_id, source)

    async def check_light_command(self, device_id: str, command: LightCommand) -> None:
        """Raise UnsupportedCommandError if the device cannot do what is asked."""
        capabilities = set((await self.get_device(device_id)).capabilities)
        missing = []
        if command.has_color() and Capability.COLOR.value not in capabilities:
            missing.append("color")
        if command.has_white() and Capability.COLOR_TEMP.value not in capabilities:
            missing.append("white (color temperature)")
        if command.brightness is not None and Capability.BRIGHTNESS.value not in capabilities:
            missing.append("brightness")
        if command.power is not None and Capability.ON_OFF.value not in capabilities:
            missing.append("on/off")
        if missing:
            raise UnsupportedCommandError(f"This device does not support: {', '.join(missing)}")

    async def set_light(self, device_id: str, command: LightCommand, source: str = "user") -> bool:
        """True if the device acknowledged. Raises DeviceNotFoundError if unknown."""
        coordinator = self._coordinator_for(device_id)
        await self._guard(device_id, source)
        return await coordinator.set_light(device_id, command)

    async def stream_light(
        self, device_id: str, brightness: int | None = None, hex_color: str | None = None, source: str = "stream"
    ) -> None:
        """Fire-and-forget color/brightness at a high rate. Raises DeviceNotFoundError if unknown."""
        coordinator = self._coordinator_for(device_id)
        await self._guard(device_id, source)
        await coordinator.stream_light(device_id, brightness, hex_color)

    async def toggle(self, device_id: str, source: str = "user") -> bool:
        coordinator = self._coordinator_for(device_id)
        await self._guard(device_id, source)
        return await coordinator.toggle(device_id)

    # --- events -------------------------------------------------------------
    def subscribe_ws(self) -> asyncio.Queue[Json]:
        queue: asyncio.Queue[Json] = asyncio.Queue[Json](maxsize=200)
        self._ws_queues.add(queue)
        return queue

    def unsubscribe_ws(self, queue: asyncio.Queue[Json]) -> None:
        self._ws_queues.discard(queue)

    async def _on_event(self, event: DeviceEvent) -> None:
        message = {"type": event.kind, "device_id": event.device_id, "data": event.data}
        for queue in list(self._ws_queues):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("A WebSocket client is too slow, dropping a message")
        for handler in list(self._event_handlers):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Event handler failed for %s", event)
