"""One order for many lights: a room, a group, the whole home."""

import asyncio

from app.core.errors import DeviceNotFoundError, DeviceUnreachableError
from app.protocols.base import Capability, LightCommand
from app.schemas.device import DeviceOut
from app.schemas.lights import LightsIn

from .hub import Hub

MAX_BRIGHTNESS = 254  # 255 is not a valid ZCL level
UNKNOWN_BRIGHTNESS = MAX_BRIGHTNESS // 2  # a light that never reported its level


def command_for(device: DeviceOut, order: LightsIn) -> LightCommand | None:
    """What this device must do for the order, or None when the order does not concern it
    (a socket does not dim, a light that is off does not get dimmer)."""
    capabilities = set(device.capabilities)
    if Capability.ON_OFF.value not in capabilities:
        return None
    dims = Capability.BRIGHTNESS.value in capabilities
    command = LightCommand(power=order.power, transition_time=order.transition_time)

    if order.brightness is not None and dims:
        command.brightness = min(order.brightness, MAX_BRIGHTNESS)
        command.power = True if order.power is None else order.power
    elif order.brightness_step is not None and dims:
        delta = round(order.brightness_step * MAX_BRIGHTNESS / 100)
        if device.state.power is False:
            if delta <= 0 or order.power is False:
                return command if order.power is not None else None
            command.power = True  # brighter on a light that is off: it comes on at that level
            command.brightness = max(1, min(delta, MAX_BRIGHTNESS))
        else:
            current = device.state.brightness if device.state.brightness is not None else UNKNOWN_BRIGHTNESS
            command.brightness = max(1, min(current + delta, MAX_BRIGHTNESS))

    if command.power is None and command.brightness is None:
        return None  # a brightness order and a device that does not dim
    return command


async def control(hub: Hub, devices: list[DeviceOut], order: LightsIn) -> dict[str, bool]:
    """Send the order to every device it concerns, at once. Maps device id -> did it acknowledge."""
    targets = [(d.id, c) for d in devices if (c := command_for(d, order)) is not None]

    async def send(device_id: str, command: LightCommand) -> bool:
        try:
            return await hub.set_light(device_id, command)
        except (DeviceNotFoundError, DeviceUnreachableError):
            return False

    results = await asyncio.gather(*(send(device_id, command) for device_id, command in targets))
    return {device_id: ok for (device_id, _), ok in zip(targets, results, strict=True)}
