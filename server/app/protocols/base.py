"""Protocol-agnostic building blocks.

Every protocol (one today, others later) implements `BaseCoordinator`. The rest
of the server (REST routes, scenes, scheduler, buttons, WebSocket) only talks to
the `Hub`, which only talks to `BaseCoordinator`.
"""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.types import Json

logger = logging.getLogger(__name__)


class Capability(StrEnum):
    ON_OFF = "on_off"
    BRIGHTNESS = "brightness"
    COLOR = "color"
    COLOR_TEMP = "color_temp"
    TEMPERATURE = "temperature"
    BUTTON = "button"
    BATTERY = "battery"


class DeviceType(StrEnum):
    BULB = "BULB"
    POWER_SOCKET = "POWER_SOCKET"
    TEMPERATURE_SENSOR = "TEMPERATURE_SENSOR"
    BUTTON = "BUTTON"
    UNKNOWN = "UNKNOWN"


def device_type_from_capabilities(capabilities: set[Capability]) -> DeviceType:
    if Capability.ON_OFF in capabilities and (
        Capability.BRIGHTNESS in capabilities
        or Capability.COLOR in capabilities
        or Capability.COLOR_TEMP in capabilities
    ):
        return DeviceType.BULB
    if Capability.ON_OFF in capabilities:
        return DeviceType.POWER_SOCKET
    if Capability.TEMPERATURE in capabilities:
        return DeviceType.TEMPERATURE_SENSOR
    if Capability.BUTTON in capabilities:
        return DeviceType.BUTTON
    return DeviceType.UNKNOWN


@dataclass
class LightCommand:
    """What to do with a light. Fields left to None are not touched."""

    power: bool | None = None
    brightness: int | None = None  # 0..255
    hue: float | None = None  # 0..360
    saturation: float | None = None  # 0..100
    hex_color: str | None = None  # "#rrggbb"
    color_temp_kelvin: int | None = None  # white light
    transition_time: float = 0  # seconds
    # Do not send the brightness again when the light already has it (animations: a level command sent
    # just after a color one disturbs the color glide on many bulbs).
    skip_same_level: bool = False

    def has_color(self) -> bool:
        return self.hex_color is not None or (self.hue is not None and self.saturation is not None)

    def has_white(self) -> bool:
        return self.color_temp_kelvin is not None

    def touches_light(self) -> bool:
        return self.has_color() or self.has_white() or self.brightness is not None


@dataclass
class DeviceEvent:
    device_id: str
    kind: str  # "state" | "button" | "joined" | "left"
    data: Json = field(default_factory=dict)


EventCallback = Callable[[DeviceEvent], Awaitable[None] | None]


class BaseCoordinator(ABC):
    """A radio/protocol able to list devices, command them and report events."""

    protocol: str = "base"

    def __init__(self) -> None:
        self._listeners: list[EventCallback] = []
        self._tasks: set[asyncio.Task[None]] = set()

    # --- events -------------------------------------------------------------
    def subscribe(self, callback: EventCallback) -> None:
        self._listeners.append(callback)

    def emit(self, event: DeviceEvent) -> None:
        """Dispatch an event to every subscriber. Must be called inside the loop."""
        for callback in list(self._listeners):
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    task = asyncio.ensure_future(result)
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
            except Exception:
                logger.exception("Event listener failed for %s", event)

    def spawn(self, coroutine: Coroutine[Any, Any, None]) -> None:
        """Run a coroutine in the background, keeping a reference so it is not garbage collected."""
        task = asyncio.ensure_future(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # --- lifecycle ----------------------------------------------------------
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    # --- devices ------------------------------------------------------------
    @abstractmethod
    async def list_devices(self) -> list[Json]:
        """Simple description of every device (never the coordinator itself)."""

    @abstractmethod
    async def get_device(self, device_id: str) -> Json | None:
        """Detailed description of one device, or None if it is unknown."""

    @abstractmethod
    def owns(self, device_id: str) -> bool: ...

    @abstractmethod
    async def remove_device(self, device_id: str) -> None:
        """Take the device off the network (it is asked to leave) and forget it."""

    @abstractmethod
    async def permit_join(self, seconds: int) -> None: ...

    @abstractmethod
    async def set_light(self, device_id: str, command: LightCommand) -> bool:
        """Returns True only if the device acknowledged the command."""

    async def stream_light(self, device_id: str, brightness: int | None = None, hex_color: str | None = None) -> None:
        """Color and brightness for live effects (music): the newest value matters more than an
        acknowledgement. Protocols that can send without waiting for an answer should override this."""
        await self.set_light(device_id, LightCommand(brightness=brightness, hex_color=hex_color))

    @abstractmethod
    async def toggle(self, device_id: str) -> bool: ...

    @abstractmethod
    async def refresh(self, device_id: str) -> Json | None:
        """Ask the device for its current readings, return its description."""

    @abstractmethod
    def info(self) -> dict[str, Any]:
        """Coordinator status for the /coordinator endpoint."""
