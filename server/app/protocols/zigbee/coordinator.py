import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.core.errors import RadioNotReadyError
from app.core.types import Json
from app.protocols.base import (
    BaseCoordinator,
    Capability,
    DeviceEvent,
    LightCommand,
    device_type_from_capabilities,
)
from app.services.device_meta import DeviceMetaService

from .device import (
    COLOR,
    LEVEL_CONTROL,
    ON_OFF,
    POWER_CONFIGURATION,
    SCENES,
    TEMPERATURE_MEASUREMENT,
    ZDevice,
    mireds_to_kelvin,
)

logger = logging.getLogger(__name__)

RADIO_RETRY_DELAY = 30
PROBE_TIMEOUT = 15
INVALID_TEMPERATURE = -32768  # ZCL "unknown" marker (0x8000)


class _ClusterListener:
    """zigpy calls these when a cluster receives a report or a command."""

    def __init__(self, coordinator: "ZigbeeCoordinator", ieee: str, cluster: Any) -> None:
        self.coordinator = coordinator
        self.ieee = ieee
        self.cluster = cluster

    def attribute_updated(self, attrid: int, value: Any, _timestamp: float | None = None) -> None:
        self.coordinator._on_attribute(self.ieee, self.cluster, attrid, value)

    def cluster_command(self, _tsn: int, command_id: int, args: Any) -> None:
        self.coordinator._on_cluster_command(self.ieee, self.cluster, command_id, args)


class ZigbeeCoordinator(BaseCoordinator):
    protocol = "zigbee"

    def __init__(self, settings: Settings, meta: DeviceMetaService) -> None:
        super().__init__()
        self.settings = settings
        self.meta = meta
        self.app: Any = None
        self._starting_task: asyncio.Task[None] | None = None
        self._state: dict[str, Json] = {}
        self._online: dict[str, bool | None] = {}
        self._listening: set[tuple[str, int, int, str]] = set()
        self._lamps: dict[str, asyncio.Lock] = {}
        self._discovery_until = 0.0
        self.last_error: str | None = None

    # --- lifecycle ----------------------------------------------------------
    async def start(self) -> None:
        """Start the radio. If the dongle is not available, keep retrying in the
        background so the server stays usable and recovers when it is plugged in."""
        if not await self._start_radio():
            self._starting_task = asyncio.ensure_future(self._retry_start())

    async def _retry_start(self) -> None:
        while True:
            await asyncio.sleep(RADIO_RETRY_DELAY)
            if await self._start_radio():
                return

    async def _start_radio(self) -> bool:
        from zigpy_znp.zigbee.application import ControllerApplication

        logger.info(
            "Starting the Zigbee radio on %s (%s baud)",
            self.settings.z_dongle_path,
            self.settings.z_dongle_baudrate,
        )
        try:
            self.app = await ControllerApplication.new(
                {
                    "database_path": self.settings.zigbee_db_path,
                    "device": {
                        "path": self.settings.z_dongle_path,
                        "baudrate": self.settings.z_dongle_baudrate,
                    },
                },
                auto_form=True,
                start_radio=True,
            )
        except Exception as e:
            self.app = None
            self.last_error = str(e) or type(e).__name__
            logger.error("Zigbee radio unavailable: %s (retry in %ss)", self.last_error, RADIO_RETRY_DELAY)
            return False

        self.last_error = None
        self.app.add_listener(self)
        for zdev in self._zigpy_devices():
            self._attach_listeners(zdev)
        logger.info("Zigbee radio ready, %d device(s) known", len(self._zigpy_devices()))
        self.spawn(self._probe_all())
        return True

    async def stop(self) -> None:
        if self._starting_task:
            self._starting_task.cancel()
        if self.app:
            await self.app.shutdown()
            self.app = None

    # --- zigpy application callbacks ----------------------------------------
    def device_joined(self, device: Any) -> None:
        logger.info("Device joined: %s", device.ieee)

    def device_initialized(self, device: Any) -> None:
        self._attach_listeners(device)
        self.spawn(self._setup_new_device(device))

    def device_left(self, device: Any) -> None:
        self.emit(DeviceEvent(str(device.ieee), "left"))

    def device_removed(self, device: Any) -> None:
        self.emit(DeviceEvent(str(device.ieee), "left"))

    async def _setup_new_device(self, zdev: Any) -> None:
        await self._probe(zdev)
        await self._configure(zdev)
        self.emit(DeviceEvent(str(zdev.ieee), "joined"))

    # --- device access ------------------------------------------------------
    def _zigpy_devices(self) -> list[Any]:
        if not self.app:
            return []
        return [d for d in self.app.devices.values() if d.nwk != 0x0000]

    def _find(self, device_id: str) -> Any:
        for zdev in self._zigpy_devices():
            if str(zdev.ieee).lower() == device_id.lower():
                return zdev
        return None

    def owns(self, device_id: str) -> bool:
        return self._find(device_id) is not None

    def _zdevice(self, zdev: Any) -> ZDevice:
        return ZDevice(zdev, self.meta.get(str(zdev.ieee)))

    # --- description --------------------------------------------------------
    def _describe(self, zdev: Any, detailed: bool = False) -> Json:
        ieee = str(zdev.ieee)
        z = self._zdevice(zdev)
        caps = z.capabilities()
        manufacturer = zdev.manufacturer or ""
        model = zdev.model or ""
        description = {
            "id": ieee,
            "protocol": self.protocol,
            "name": f"{manufacturer} {model}".strip() or ieee,
            "model": model,
            "manufacturer": manufacturer,
            "type": device_type_from_capabilities(caps).value,
            "capabilities": sorted(c.value for c in caps),
            "online": self._online.get(ieee),
            "nwk": f"0x{zdev.nwk:04X}",
            "last_seen": (
                datetime.fromtimestamp(zdev.last_seen).isoformat(timespec="seconds") if zdev.last_seen else None
            ),
            "lqi": zdev.lqi,
            "rssi": zdev.rssi,
            "state": self._full_state(zdev, caps),
        }
        if Capability.COLOR_TEMP in caps:
            description["color_temp_range_kelvin"] = list(z.kelvin_range())
        if detailed:
            description["endpoints"] = {
                str(ep_id): {
                    "profile_id": ep.profile_id,
                    "device_type": ep.device_type,
                    "in_clusters": [{"id": f"0x{cid:04X}", "name": c.name} for cid, c in ep.in_clusters.items()],
                    "out_clusters": [{"id": f"0x{cid:04X}", "name": c.name} for cid, c in ep.out_clusters.items()],
                }
                for ep_id, ep in zdev.endpoints.items()
                if ep_id != 0
            }
        return description

    def _full_state(self, zdev: Any, caps: set[Capability]) -> Json:
        ieee = str(zdev.ieee)
        state = dict(self._state.get(ieee, {}))
        # fall back on the values zigpy cached in its database (last reports)
        if Capability.TEMPERATURE in caps and "temperature" not in state:
            cluster = self._zdevice(zdev).in_cluster(TEMPERATURE_MEASUREMENT)
            temperature = self._temperature_from(cluster.get("measured_value") if cluster else None)
            if temperature is not None:
                state["temperature"] = temperature
        if Capability.BATTERY in caps and "battery" not in state:
            cluster = self._zdevice(zdev).in_cluster(POWER_CONFIGURATION)
            battery = self._battery_from(cluster.get("battery_percentage_remaining") if cluster else None)
            if battery is not None:
                state["battery"] = battery
        return state

    async def list_devices(self) -> list[Json]:
        return [self._describe(zdev) for zdev in self._zigpy_devices()]

    async def get_device(self, device_id: str) -> Json | None:
        zdev = self._find(device_id)
        return self._describe(zdev, detailed=True) if zdev else None

    def info(self) -> dict[str, Any]:
        remaining = max(0, int(self._discovery_until - time.monotonic()))
        return {
            "protocol": self.protocol,
            "ready": self.app is not None,
            "port": self.settings.z_dongle_path,
            "baudrate": self.settings.z_dongle_baudrate,
            "last_error": self.last_error,
            "discovery_remaining": remaining,
            "devices": len(self._zigpy_devices()),
        }

    # --- state --------------------------------------------------------------
    def _set_state(self, ieee: str, **values: Any) -> None:
        state = self._state.setdefault(ieee, {})
        changed = {k: v for k, v in values.items() if state.get(k) != v}
        if changed:
            state.update(changed)
            self.emit(DeviceEvent(ieee, "state", {"state": Json(state), "online": self._online.get(ieee)}))

    def _set_online(self, ieee: str, online: bool) -> None:
        if self._online.get(ieee) != online:
            self._online[ieee] = online
            self.emit(DeviceEvent(ieee, "state", {"state": Json(self._state.get(ieee, {})), "online": online}))

    @staticmethod
    def _temperature_from(raw: Any) -> float | None:
        if raw is None or int(raw) == INVALID_TEMPERATURE:
            return None
        return round(int(raw) / 100, 1)

    @staticmethod
    def _battery_from(raw: Any) -> int | None:
        if raw is None or int(raw) == 0xFF:
            return None
        return min(int(raw) // 2, 100)  # ZCL reports half-percents

    def _on_attribute(self, ieee: str, cluster: Any, attrid: int | str, value: Any) -> None:
        attribute = cluster.find_attribute(attrid)
        name = attribute.name if attribute else None
        if name == "on_off":
            self._set_state(ieee, power=bool(value))
        elif name == "current_level":
            self._set_state(ieee, brightness=int(value))
        elif name == "color_temperature":
            self._set_state(ieee, color_temp_kelvin=mireds_to_kelvin(int(value)))
        elif name == "measured_value" and cluster.cluster_id == TEMPERATURE_MEASUREMENT:
            temperature = self._temperature_from(value)
            if temperature is not None:
                self._set_state(ieee, temperature=temperature)
        elif name == "battery_percentage_remaining":
            battery = self._battery_from(value)
            if battery is not None:
                self._set_state(ieee, battery=battery)
        else:
            return
        self._online[ieee] = True

    def _on_cluster_command(self, ieee: str, cluster: Any, command_id: int, args: Any) -> None:
        definition = cluster.server_commands.get(command_id) or cluster.client_commands.get(command_id)
        command = definition.name if definition else f"0x{command_id:02x}"
        cluster_name = getattr(cluster, "ep_attribute", None) or f"0x{cluster.cluster_id:04x}"
        event = f"{cluster_name}.{command}"
        now = datetime.now().isoformat(timespec="seconds")
        logger.info("Button event from %s: %s %s", ieee, event, args)
        self._online[ieee] = True
        self._state.setdefault(ieee, {})["last_button"] = {"event": event, "at": now}
        self.emit(DeviceEvent(ieee, "button", {"event": event, "args": repr(args), "at": now}))

    def _attach_listeners(self, zdev: Any) -> None:
        ieee = str(zdev.ieee)
        for ep_id, endpoint in zdev.endpoints.items():
            if ep_id == 0:
                continue
            for direction, clusters in (("in", endpoint.in_clusters), ("out", endpoint.out_clusters)):
                for cluster_id, cluster in clusters.items():
                    key = (ieee, ep_id, cluster_id, direction)
                    if key in self._listening:
                        continue
                    self._listening.add(key)
                    cluster.add_listener(_ClusterListener(self, ieee, cluster))

    # --- probing / configuration -------------------------------------------
    async def _read(self, cluster: Any, attributes: list[str]) -> Json:
        try:
            success, _ = await asyncio.wait_for(cluster.read_attributes(attributes, allow_cache=False), PROBE_TIMEOUT)
            result: Json = success
            return result
        except Exception as e:
            logger.debug("Could not read %s: %s", attributes, e)
            return {}

    async def _probe_all(self) -> None:
        semaphore = asyncio.Semaphore(3)

        async def probe(zdev: Any) -> None:
            async with semaphore:
                await self._probe(zdev)

        await asyncio.gather(*(probe(z) for z in self._zigpy_devices()), return_exceptions=True)

    async def _probe(self, zdev: Any) -> None:
        """Read what the device can do (once) and its current light state."""
        ieee = str(zdev.ieee)
        z = self._zdevice(zdev)
        color = z.in_cluster(COLOR)
        if color is not None and "color_capabilities" not in z.meta:
            values = await self._read(
                color,
                ["color_capabilities", "color_temp_physical_min", "color_temp_physical_max"],
            )
            if "color_capabilities" in values:
                meta = {
                    "color_capabilities": int(values["color_capabilities"]),
                    "mireds_min": int(values.get("color_temp_physical_min") or 0) or None,
                    "mireds_max": int(values.get("color_temp_physical_max") or 0) or None,
                }
                await self.meta.save(ieee, meta)
        await self._read_light_state(zdev)

    async def _read_light_state(self, zdev: Any) -> None:
        ieee = str(zdev.ieee)
        z = self._zdevice(zdev)
        reached = False
        if (cluster := z.in_cluster(ON_OFF)) is not None:
            values = await self._read(cluster, ["on_off"])
            if "on_off" in values:
                reached = True
                self._set_state(ieee, power=bool(values["on_off"]))
        if (cluster := z.in_cluster(LEVEL_CONTROL)) is not None:
            values = await self._read(cluster, ["current_level"])
            if "current_level" in values:
                reached = True
                self._set_state(ieee, brightness=int(values["current_level"]))
        if Capability.COLOR_TEMP in z.capabilities() and (cluster := z.in_cluster(COLOR)) is not None:
            values = await self._read(cluster, ["color_temperature"])
            if values.get("color_temperature"):
                self._set_state(ieee, color_temp_kelvin=mireds_to_kelvin(int(values["color_temperature"])))
        if reached:
            self._set_online(ieee, True)

    async def _configure(self, zdev: Any) -> None:
        """Bind the clusters whose reports/commands we want to receive and set up
        reporting. Sleeping devices only answer while awake: if this fails, wake the
        device (press its button) and call POST /device/{id}/refresh."""
        ieee = str(zdev.ieee)
        for ep_id, endpoint in zdev.endpoints.items():
            if ep_id == 0:
                continue
            plan: list[tuple[Any, tuple[Any, ...]]] = []
            if TEMPERATURE_MEASUREMENT in endpoint.in_clusters:
                plan.append((endpoint.in_clusters[TEMPERATURE_MEASUREMENT], ("measured_value", 60, 900, 25)))
            if POWER_CONFIGURATION in endpoint.in_clusters:
                plan.append(
                    (endpoint.in_clusters[POWER_CONFIGURATION], ("battery_percentage_remaining", 3600, 43200, 2))
                )
            for cluster_id in (ON_OFF, LEVEL_CONTROL, SCENES):
                if cluster_id in endpoint.out_clusters and ON_OFF not in endpoint.in_clusters:
                    plan.append((endpoint.out_clusters[cluster_id], ()))
            for cluster, reporting in plan:
                try:
                    await asyncio.wait_for(cluster.bind(), PROBE_TIMEOUT)
                    if reporting:
                        await asyncio.wait_for(cluster.configure_reporting(*reporting), PROBE_TIMEOUT)
                except Exception as e:
                    logger.info("Could not configure %s on %s (asleep?): %s", cluster.name, ieee, e)

    # --- commands -----------------------------------------------------------
    async def permit_join(self, seconds: int) -> None:
        if not self.app:
            raise RadioNotReadyError("The Zigbee radio is not ready (dongle unplugged or busy?)")
        await self.app.permit(seconds)
        self._discovery_until = time.monotonic() + seconds
        logger.info("Pairing allowed for %ss", seconds)

    async def _run(self, device_id: str, action: Callable[[ZDevice], Awaitable[None]]) -> bool:
        zdev = self._find(device_id)
        if not zdev:
            return False
        ieee = str(zdev.ieee)
        try:
            # One order at a time per lamp, in the order they came: a lamp that is sent a second command while
            # the radio is still busy with the first one (a retry, a slow answer) ends the first one at once.
            async with self._lamps.setdefault(ieee, asyncio.Lock()):
                await action(self._zdevice(zdev))
        except Exception as e:
            self._set_online(ieee, False)
            logger.error("Command failed for %s: %s", ieee, str(e) or type(e).__name__)
            return False
        self._set_online(ieee, True)
        return True

    async def set_light(self, device_id: str, command: LightCommand) -> bool:
        async def action(z: ZDevice) -> None:
            zdev = self._find(device_id)
            state = self._state.get(str(zdev.ieee), {}) if zdev else {}
            await z.apply(command, state.get("power"), state.get("brightness"))

        ok = await self._run(device_id, action)
        if ok:
            values: dict[str, Any] = {}
            if command.power is False or command.brightness == 0:
                values["power"] = False
            elif command.power is True or command.touches_light():
                values["power"] = True
            if command.brightness:
                values["brightness"] = min(command.brightness, 254)
            if command.has_color():
                values.update(hue=command.hue, saturation=command.saturation, hex_color=command.hex_color)
            if command.has_white():
                values["color_temp_kelvin"] = command.color_temp_kelvin
            self._set_state(str(self._find(device_id).ieee), **values)
        return ok

    async def stream_light(self, device_id: str, brightness: int | None = None, hex_color: str | None = None) -> None:
        zdev = self._find(device_id)
        if not zdev:
            return
        try:
            await self._zdevice(zdev).stream(brightness, hex_color)
        except Exception as e:
            logger.debug("Streamed light failed for %s: %s", zdev.ieee, str(e) or type(e).__name__)

    async def toggle(self, device_id: str) -> bool:
        ok = await self._run(device_id, lambda z: z.toggle())
        if ok:
            zdev = self._find(device_id)
            ieee = str(zdev.ieee)
            self._set_state(ieee, power=not self._state.get(ieee, {}).get("power", False))
        return ok

    async def refresh(self, device_id: str) -> Json | None:
        zdev = self._find(device_id)
        if not zdev:
            return None
        ieee = str(zdev.ieee)
        z = self._zdevice(zdev)
        await self._configure(zdev)
        await self._read_light_state(zdev)
        if (cluster := z.in_cluster(TEMPERATURE_MEASUREMENT)) is not None:
            values = await self._read(cluster, ["measured_value"])
            temperature = self._temperature_from(values.get("measured_value"))
            if temperature is not None:
                self._set_state(ieee, temperature=temperature)
                self._set_online(ieee, True)
        if (cluster := z.in_cluster(POWER_CONFIGURATION)) is not None:
            values = await self._read(cluster, ["battery_percentage_remaining"])
            battery = self._battery_from(values.get("battery_percentage_remaining"))
            if battery is not None:
                self._set_state(ieee, battery=battery)
        return self._describe(zdev)
