import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.protocols.base import DeviceEvent, LightCommand
from app.protocols.z.coordinator import ZCoordinator, _ClusterListener
from app.protocols.z.device import (
    COLOR,
    LEVEL_CONTROL,
    ON_OFF,
    POWER_CONFIGURATION,
    TEMPERATURE_MEASUREMENT,
)
from tests.conftest import fake_cluster, fake_zigpy_device

IEEE = "00:11:22:33:44:55:66:77"


class FakeMeta:
    def __init__(self):
        self.data = {}

    def get(self, device_id):
        return self.data.get(device_id, {})

    async def save(self, device_id, data):
        self.data[device_id] = data


def make(devices):
    coordinator = ZCoordinator(Settings(enable_z=False, _env_file=None), FakeMeta())
    coordinator.app = SimpleNamespace(
        devices={d.ieee: d for d in devices},
        permit=None,
    )
    events: list[DeviceEvent] = []
    coordinator.subscribe(events.append)
    return coordinator, events


def sensor():
    temperature = fake_cluster(TEMPERATURE_MEASUREMENT, "temperature", "temperature", measured_value=2150)
    battery = fake_cluster(POWER_CONFIGURATION, "power", "power", battery_percentage_remaining=180)
    return fake_zigpy_device(IEEE, [temperature, battery]), temperature, battery


def remote():
    onoff = fake_cluster(ON_OFF, "on_off", "on_off")
    onoff.server_commands = {0x02: SimpleNamespace(name="toggle")}
    return fake_zigpy_device(IEEE, [fake_cluster(POWER_CONFIGURATION)], [onoff]), onoff


async def test_the_coordinator_itself_is_not_listed():
    zdev, *_ = sensor()
    coordinator_node = fake_zigpy_device("ff:ff:ff:ff:ff:ff:ff:ff", nwk=0x0000)
    coordinator, _ = make([zdev, coordinator_node])
    devices = await coordinator.list_devices()
    assert [d["id"] for d in devices] == [IEEE]
    assert not coordinator.owns("ff:ff:ff:ff:ff:ff:ff:ff")


async def test_sensor_description_uses_values_cached_by_zigpy():
    zdev, *_ = sensor()
    coordinator, _ = make([zdev])
    device = (await coordinator.list_devices())[0]
    assert device["type"] == "TEMPERATURE_SENSOR"
    assert device["state"] == {"temperature": 21.5, "battery": 90}  # 180 half-percents


async def test_temperature_report_updates_state_and_emits():
    zdev, temperature, _ = sensor()
    coordinator, events = make([zdev])
    coordinator._attach_listeners(zdev)

    listener = temperature.listeners[0]
    listener.attribute_updated("measured_value", 2310)

    state = (await coordinator.get_device(IEEE))["state"]
    assert state["temperature"] == 23.1
    assert events[-1].kind == "state" and events[-1].data["state"]["temperature"] == 23.1
    assert events[-1].device_id == IEEE


async def test_invalid_temperature_and_battery_markers_are_ignored():
    zdev, temperature, battery = sensor()
    coordinator, events = make([zdev])
    coordinator._attach_listeners(zdev)
    temperature.listeners[0].attribute_updated("measured_value", -32768)
    battery.listeners[0].attribute_updated("battery_percentage_remaining", 0xFF)
    assert events == []


async def test_battery_report():
    zdev, _, battery = sensor()
    coordinator, events = make([zdev])
    coordinator._attach_listeners(zdev)
    battery.listeners[0].attribute_updated("battery_percentage_remaining", 150)
    assert events[-1].data["state"]["battery"] == 75


async def test_button_press_emits_an_event_and_is_remembered():
    zdev, onoff = remote()
    coordinator, events = make([zdev])
    coordinator._attach_listeners(zdev)

    onoff.listeners[0].cluster_command(7, 0x02, [])

    assert events[-1].kind == "button"
    assert events[-1].data["event"] == "on_off.toggle"
    device = await coordinator.get_device(IEEE)
    assert device["type"] == "BUTTON"
    assert device["state"]["last_button"]["event"] == "on_off.toggle"


async def test_unknown_button_command_still_reported_by_id():
    zdev, onoff = remote()
    coordinator, events = make([zdev])
    coordinator._attach_listeners(zdev)
    onoff.listeners[0].cluster_command(1, 0x7F, ["x"])
    assert events[-1].data["event"] == "on_off.0x7f"


async def test_listeners_are_attached_once_per_cluster():
    zdev, temperature, _ = sensor()
    coordinator, _ = make([zdev])
    coordinator._attach_listeners(zdev)
    coordinator._attach_listeners(zdev)
    assert len(temperature.listeners) == 1


async def test_set_light_tracks_state_and_online():
    onoff, level, color = fake_cluster(ON_OFF), fake_cluster(LEVEL_CONTROL), fake_cluster(COLOR)
    zdev = fake_zigpy_device(IEEE, [onoff, level, color])
    coordinator, events = make([zdev])

    assert await coordinator.set_light(IEEE, LightCommand(power=True, brightness=100))
    device = await coordinator.get_device(IEEE)
    assert device["online"] is True
    assert device["state"]["power"] is True and device["state"]["brightness"] == 100
    assert any(e.kind == "state" for e in events)

    onoff.fail = RuntimeError("MAC_NO_ACK")
    assert not await coordinator.set_light(IEEE, LightCommand(power=False))
    assert (await coordinator.get_device(IEEE))["online"] is False


async def test_toggle_flips_the_tracked_power():
    onoff = fake_cluster(ON_OFF)
    zdev = fake_zigpy_device(IEEE, [onoff])
    coordinator, _ = make([zdev])
    assert await coordinator.toggle(IEEE)
    assert (await coordinator.get_device(IEEE))["state"]["power"] is True
    assert await coordinator.toggle(IEEE)
    assert (await coordinator.get_device(IEEE))["state"]["power"] is False
    assert onoff.commands == [(0x02, ()), (0x02, ())]


async def test_commands_on_unknown_devices_fail_cleanly():
    coordinator, _ = make([])
    assert not await coordinator.set_light("nope", LightCommand(power=True))
    assert not await coordinator.toggle("nope")
    assert await coordinator.get_device("nope") is None


async def test_permit_join_requires_the_radio():
    from app.core.errors import RadioNotReadyError

    coordinator = ZCoordinator(Settings(enable_z=False, _env_file=None), FakeMeta())
    with pytest.raises(RadioNotReadyError):
        await coordinator.permit_join(30)
    assert coordinator.info()["ready"] is False


def test_cluster_listener_ignores_the_zigpy_timestamp():
    calls = []
    coordinator = SimpleNamespace(
        _on_attribute=lambda *a: calls.append(a), _on_cluster_command=lambda *a: calls.append(a)
    )
    listener = _ClusterListener(coordinator, IEEE, "cluster")
    listener.attribute_updated(1, 2, 123456.0)
    listener.cluster_command(5, 6, [])
    assert calls == [(IEEE, "cluster", 1, 2), (IEEE, "cluster", 6, [])]


async def test_a_lamp_is_sent_one_command_at_a_time_in_the_order_they_came():
    """A lamp that is sent a command while the radio is busy with the previous one ends it at once."""
    onoff, level, color = fake_cluster(ON_OFF), fake_cluster(LEVEL_CONTROL), fake_cluster(COLOR)
    zdev = fake_zigpy_device(IEEE, [onoff, level, color])
    coordinator, _ = make([zdev])
    running = 0
    most = 0
    order: list[int] = []

    async def slow(command_id, *args, **options):
        nonlocal running, most
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.02)  # the radio is busy with this one
        order.append(args[0])
        running -= 1

    level.command = slow
    results = await asyncio.gather(
        *(coordinator.set_light(IEEE, LightCommand(brightness=value)) for value in (10, 20, 30, 40))
    )
    assert all(results)
    assert most == 1  # never two exchanges at once on the same lamp
    assert order == [10, 20, 30, 40]  # and in the order they came


async def test_remove_device_asks_zigpy_and_hides_it_at_once():
    zdev, *_ = sensor()
    coordinator, _ = make([zdev])
    asked = []

    async def remove(ieee):
        asked.append(ieee)  # zigpy keeps the device in its list for a few seconds more

    coordinator.app.remove = remove
    await coordinator.remove_device(IEEE)
    assert asked == [zdev.ieee]
    assert not coordinator.owns(IEEE)
    assert await coordinator.list_devices() == []

    coordinator.device_joined(zdev)  # it is paired again
    assert coordinator.owns(IEEE)
