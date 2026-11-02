"""Thin adapter for a zigpy device: what it can do and how to command it."""

import asyncio
import logging
from typing import Any

from zigpy.zcl import foundation

from app.core.types import Json
from app.protocols.base import Capability, LightCommand
from app.utils.color_converter import ColorConverter

logger = logging.getLogger(__name__)

# ZCL cluster ids
BASIC = 0x0000
POWER_CONFIGURATION = 0x0001
SCENES = 0x0005
ON_OFF = 0x0006
LEVEL_CONTROL = 0x0008
COLOR = 0x0300
TEMPERATURE_MEASUREMENT = 0x0402

# OnOff commands
CMD_OFF, CMD_ON, CMD_TOGGLE = 0x00, 0x01, 0x02
# LevelControl command
CMD_MOVE_TO_LEVEL_WITH_ON_OFF = 0x04
# Color commands
CMD_MOVE_TO_COLOR = 0x07
CMD_MOVE_TO_COLOR_TEMP = 0x0A

# Color capabilities bit field (ZCL)
CAP_HUE_SAT, CAP_ENHANCED_HUE, CAP_COLOR_LOOP, CAP_XY, CAP_COLOR_TEMP = 1, 2, 4, 8, 16

DEFAULT_MIREDS_RANGE = (153, 500)  # ~6500 K .. 2000 K
COMMAND_TIMEOUT = 20


def kelvin_to_mireds(kelvin: float) -> int:
    return round(1_000_000 / max(kelvin, 1))


def mireds_to_kelvin(mireds: float) -> int:
    return round(1_000_000 / max(mireds, 1))


class ZDevice:
    """`meta` holds what was probed from the device (color capabilities, mireds range)."""

    def __init__(self, zdev: Any, meta: Json | None = None) -> None:
        self.zdev = zdev
        self.meta = meta or {}

    @property
    def ieee(self) -> str:
        return str(self.zdev.ieee)

    # --- clusters -----------------------------------------------------------
    def _endpoints(self) -> list[Any]:
        return [ep for ep_id, ep in self.zdev.endpoints.items() if ep_id != 0]  # 0 = ZDO

    def in_cluster(self, cluster_id: int) -> Any:
        for endpoint in self._endpoints():
            if cluster_id in endpoint.in_clusters:
                return endpoint.in_clusters[cluster_id]
        return None

    def has_in(self, cluster_id: int) -> bool:
        return self.in_cluster(cluster_id) is not None

    def has_out(self, cluster_id: int) -> bool:
        return any(cluster_id in ep.out_clusters for ep in self._endpoints())

    # --- capabilities -------------------------------------------------------
    def capabilities(self) -> set[Capability]:
        caps: set[Capability] = set()
        if self.has_in(ON_OFF):
            caps.add(Capability.ON_OFF)
        if self.has_in(LEVEL_CONTROL):
            caps.add(Capability.BRIGHTNESS)
        if self.has_in(COLOR):
            color_caps = self.meta.get("color_capabilities")
            if color_caps is None:  # not probed (yet): assume a full color + white bulb
                caps.update({Capability.COLOR, Capability.COLOR_TEMP})
            else:
                if color_caps & (CAP_HUE_SAT | CAP_ENHANCED_HUE | CAP_XY):
                    caps.add(Capability.COLOR)
                if color_caps & CAP_COLOR_TEMP:
                    caps.add(Capability.COLOR_TEMP)
        if self.has_in(TEMPERATURE_MEASUREMENT):
            caps.add(Capability.TEMPERATURE)
        if self.has_in(POWER_CONFIGURATION):
            caps.add(Capability.BATTERY)
        if Capability.ON_OFF not in caps and any(self.has_out(c) for c in (ON_OFF, LEVEL_CONTROL, SCENES)):
            caps.add(Capability.BUTTON)
        return caps

    def mireds_range(self) -> tuple[int, int]:
        low = self.meta.get("mireds_min") or DEFAULT_MIREDS_RANGE[0]
        high = self.meta.get("mireds_max") or DEFAULT_MIREDS_RANGE[1]
        return low, high

    def kelvin_range(self) -> tuple[int, int]:
        low, high = self.mireds_range()
        return mireds_to_kelvin(high), mireds_to_kelvin(low)

    # --- commands -----------------------------------------------------------
    async def command(self, cluster_id: int, command_id: int, *args: Any, expect_reply: bool = True) -> None:
        """Send one cluster command. Raises if the device did not acknowledge it
        (unless `expect_reply` is False: sent and not waited for)."""
        cluster = self.in_cluster(cluster_id)
        if cluster is None:
            raise RuntimeError(f"{self.ieee} has no cluster 0x{cluster_id:04X}")
        options = {} if expect_reply else {"expect_reply": False}
        result = await asyncio.wait_for(cluster.command(command_id, *args, **options), COMMAND_TIMEOUT)
        status = getattr(result, "status", None)
        if isinstance(status, foundation.Status) and status != foundation.Status.SUCCESS:
            raise RuntimeError(f"{self.ieee} answered {status.name}")

    async def toggle(self) -> None:
        await self.command(ON_OFF, CMD_TOGGLE)

    async def stream(self, brightness: int | None = None, hex_color: str | None = None) -> None:
        """Instant color and/or brightness, sent without waiting for the bulb to answer (live effects)."""
        caps = self.capabilities()
        if hex_color is not None and Capability.COLOR in caps:
            hue, saturation = ColorConverter.hex_to_hue_saturation(hex_color)
            x, y = ColorConverter.hue_saturation_to_xy(hue, saturation)
            await self.command(COLOR, CMD_MOVE_TO_COLOR, x, y, 0, expect_reply=False)
        if brightness is not None and Capability.BRIGHTNESS in caps:
            level = max(0, min(brightness, 254))  # 255 is "invalid" in ZCL
            await self.command(LEVEL_CONTROL, CMD_MOVE_TO_LEVEL_WITH_ON_OFF, level, 0, expect_reply=False)

    async def apply(self, cmd: LightCommand, is_on: bool | None = None, known_level: int | None = None) -> None:
        """Apply a light command. Parts the device cannot do are skipped.
        `is_on` and `known_level` are what we know of the light. A light that is already on is not sent "on" again,
        because many bulbs cut the running fade when they receive it. A light that is off gets its
        color first and is turned on afterwards (by the level command, or by "on" when there is
        none): turning it on first would flash its previous color, often white.
        Raises on the first command the device does not acknowledge."""
        caps = self.capabilities()
        transition = max(0, min(int(cmd.transition_time * 10), 0xFFFE))  # 1/10 s

        if cmd.power is False:
            if Capability.ON_OFF in caps:
                await self.command(ON_OFF, CMD_OFF)
            return

        same_level = (
            cmd.skip_same_level
            and is_on is True
            and cmd.brightness is not None
            and cmd.brightness > 0
            and min(cmd.brightness, 254) == known_level
        )
        level_sent = cmd.brightness is not None and Capability.BRIGHTNESS in caps and not same_level
        turn_on = Capability.ON_OFF in caps and is_on is not True and (cmd.power is True or cmd.touches_light())
        # A lamp that is known to be off shows nothing of its color: it changes at once, so that only one glide
        # (the brightness one) is sent. A second glide command would end the first one at once on the lamp.
        color_transition = 0 if is_on is False else transition

        if cmd.has_color() and Capability.COLOR in caps:
            if cmd.hex_color is not None:
                hue, saturation = ColorConverter.hex_to_hue_saturation(cmd.hex_color)
            else:
                assert cmd.hue is not None  # has_color()
                assert cmd.saturation is not None
                hue, saturation = cmd.hue, cmd.saturation
            x, y = ColorConverter.hue_saturation_to_xy(hue, saturation)
            logger.info("%s: color hue=%s saturation=%s over %ss", self.ieee, hue, saturation, cmd.transition_time)
            await self.command(COLOR, CMD_MOVE_TO_COLOR, x, y, color_transition)
        elif cmd.has_white() and Capability.COLOR_TEMP in caps:
            low, high = self.mireds_range()
            assert cmd.color_temp_kelvin is not None  # has_white()
            mireds = max(low, min(kelvin_to_mireds(cmd.color_temp_kelvin), high))
            logger.info("%s: white %s K over %ss", self.ieee, cmd.color_temp_kelvin, cmd.transition_time)
            await self.command(COLOR, CMD_MOVE_TO_COLOR_TEMP, mireds, color_transition)

        if turn_on and not level_sent:  # the level command below turns the light on by itself
            await self.command(ON_OFF, CMD_ON)

        if level_sent and cmd.brightness is not None:
            level = max(0, min(cmd.brightness, 254))  # 255 is "invalid" in ZCL
            logger.info("%s: brightness %s over %ss", self.ieee, level, cmd.transition_time)
            await self.command(LEVEL_CONTROL, CMD_MOVE_TO_LEVEL_WITH_ON_OFF, level, transition)
