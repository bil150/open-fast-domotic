import pytest
from zigpy.zcl import foundation

from app.protocols.base import Capability, LightCommand, device_type_from_capabilities
from app.protocols.z.device import (
    COLOR,
    LEVEL_CONTROL,
    ON_OFF,
    POWER_CONFIGURATION,
    SCENES,
    TEMPERATURE_MEASUREMENT,
    ZDevice,
    kelvin_to_mireds,
    mireds_to_kelvin,
)
from tests.conftest import fake_cluster, fake_zigpy_device


def bulb(meta=None, extra=()):
    onoff, level, color = fake_cluster(ON_OFF), fake_cluster(LEVEL_CONTROL), fake_cluster(COLOR)
    zdev = fake_zigpy_device("00:11:22:33:44:55:66:77", [onoff, level, color, *extra])
    return ZDevice(zdev, meta), onoff, level, color


def sent(cluster):
    return cluster.commands


def test_kelvin_mireds_roundtrip():
    assert kelvin_to_mireds(2700) == 370
    assert mireds_to_kelvin(370) == 2703


def test_color_bulb_capabilities_default_to_full():
    z, *_ = bulb()
    assert z.capabilities() == {Capability.ON_OFF, Capability.BRIGHTNESS, Capability.COLOR, Capability.COLOR_TEMP}
    assert device_type_from_capabilities(z.capabilities()).value == "BULB"


def test_probed_color_capabilities_are_respected():
    white_only, *_ = bulb({"color_capabilities": 16})  # color temperature only
    assert Capability.COLOR not in white_only.capabilities()
    assert Capability.COLOR_TEMP in white_only.capabilities()
    color_only, *_ = bulb({"color_capabilities": 8})  # xy only
    assert Capability.COLOR in color_only.capabilities()
    assert Capability.COLOR_TEMP not in color_only.capabilities()


def test_socket_sensor_and_button_types():
    socket = ZDevice(fake_zigpy_device("a", [fake_cluster(ON_OFF)]))
    assert device_type_from_capabilities(socket.capabilities()).value == "POWER_SOCKET"

    sensor = ZDevice(fake_zigpy_device("b", [fake_cluster(TEMPERATURE_MEASUREMENT), fake_cluster(POWER_CONFIGURATION)]))
    assert sensor.capabilities() == {Capability.TEMPERATURE, Capability.BATTERY}
    assert device_type_from_capabilities(sensor.capabilities()).value == "TEMPERATURE_SENSOR"

    remote = ZDevice(
        fake_zigpy_device(
            "c",
            [fake_cluster(POWER_CONFIGURATION)],
            [fake_cluster(ON_OFF), fake_cluster(LEVEL_CONTROL), fake_cluster(SCENES)],
        )
    )
    assert Capability.BUTTON in remote.capabilities()
    assert device_type_from_capabilities(remote.capabilities()).value == "BUTTON"


def test_the_coordinator_zdo_endpoint_is_ignored():
    z, *_ = bulb()
    assert 0 in z.zdev.endpoints
    assert z.in_cluster(ON_OFF) is not None


def test_kelvin_range_uses_probed_mireds():
    z, *_ = bulb({"color_capabilities": 16, "mireds_min": 153, "mireds_max": 454})
    assert z.kelvin_range() == (2203, 6536)


async def test_color_sequence_is_on_color_level():
    z, onoff, level, color = bulb()
    await z.apply(LightCommand(power=True, hex_color="#ff0000", brightness=300, transition_time=2))
    assert sent(onoff) == []  # the level command turns the light on, after its color is set
    ((color_cmd, (x, _y, transition)),) = sent(color)
    assert color_cmd == 0x07 and 0 <= x <= 65535 and transition == 20
    assert sent(level) == [(0x04, (254, 20))]  # clamped: 255 is invalid in ZCL


async def test_a_light_known_to_be_on_is_not_sent_on_again():
    """Another "on" would cut the fade that is running on many bulbs."""
    z, onoff, level, color = bulb()
    await z.apply(LightCommand(power=True, hex_color="#ff0000", brightness=100, transition_time=2), is_on=True)
    assert sent(onoff) == []
    assert len(sent(color)) == 1 and sent(level) == [(0x04, (100, 20))]
    await z.apply(LightCommand(power=True, hex_color="#00ff00", transition_time=2), is_on=False)
    assert [c for c, _ in sent(onoff)] == [0x01]  # a light that is off still gets turned on


async def test_a_light_that_is_off_changes_color_at_once_and_only_its_brightness_glides():
    """Two glide commands to one lamp: it ends the first at once. Off, its color shows nothing anyway."""
    z, _onoff, level, color = bulb()
    await z.apply(LightCommand(power=True, hex_color="#00ff00", brightness=100, transition_time=2), is_on=False)
    ((_, (_x, _y, color_transition)),) = sent(color)
    assert color_transition == 0
    assert sent(level) == [(0x04, (100, 20))]

    z, _onoff, level, color = bulb()
    await z.apply(LightCommand(power=True, hex_color="#00ff00", brightness=100, transition_time=2), is_on=None)
    ((_, (_x, _y, color_transition)),) = sent(color)
    assert color_transition == 20  # a light whose state is unknown may be on: it glides


async def test_a_light_that_is_off_gets_its_color_before_being_turned_on():
    """Turning it on first would flash the color it had before (often white)."""
    z, onoff, level, color = bulb()
    order: list[str] = []
    for name, cluster in (("on", onoff), ("level", level), ("color", color)):
        original = cluster.command

        async def record(command_id, *args, _name=name, _original=original):
            order.append(_name)
            return await _original(command_id, *args)

        cluster.command = record
    await z.apply(LightCommand(power=True, hex_color="#00ff00", transition_time=2), is_on=False)
    assert order == ["color", "on"]
    order.clear()
    await z.apply(LightCommand(power=True, hex_color="#00ff00", brightness=100, transition_time=2), is_on=False)
    assert order == ["color", "level"]  # no separate "on": the level command does it


async def test_white_light_uses_color_temperature_clamped_to_the_bulb_range():
    z, _, level, color = bulb({"color_capabilities": 16, "mireds_min": 250, "mireds_max": 454})
    await z.apply(LightCommand(color_temp_kelvin=6500))  # 154 mireds: colder than the bulb can do
    assert sent(color) == [(0x0A, (250, 0))]
    assert sent(level) == []


async def test_power_off_sends_only_off():
    z, onoff, level, color = bulb()
    await z.apply(LightCommand(power=False, brightness=100, hex_color="#ffffff"))
    assert sent(onoff) == [(0x00, ())]
    assert sent(level) == [] and sent(color) == []


async def test_unsupported_parts_are_skipped():
    z, _onoff, level, color = bulb({"color_capabilities": 16})
    await z.apply(LightCommand(hex_color="#ff0000", brightness=50))
    assert sent(color) == []  # white-only bulb: color ignored
    assert sent(level) == [(0x04, (50, 0))]


async def test_failed_command_raises():
    z, onoff, *_ = bulb()
    onoff.fail = RuntimeError("MAC_NO_ACK")
    with pytest.raises(RuntimeError):
        await z.apply(LightCommand(power=True))


async def test_default_response_error_status_raises():
    z, onoff, *_ = bulb()

    async def refuse(command_id, *args):
        return type("Response", (), {"status": foundation.Status.UNSUP_CLUSTER_COMMAND})()

    onoff.command = refuse
    with pytest.raises(RuntimeError, match="UNSUP"):
        await z.toggle()


async def test_command_without_the_cluster_raises():
    socket = ZDevice(fake_zigpy_device("a", [fake_cluster(ON_OFF)]))
    with pytest.raises(RuntimeError, match="no cluster"):
        await socket.command(COLOR, 0x07, 1, 2, 0)


async def test_stream_sends_color_then_level_without_waiting_for_a_reply():
    z, _onoff, level, color = bulb()
    await z.stream(brightness=300, hex_color="#ff0000")
    assert [c[0] for c in sent(color)] == [0x07]
    assert sent(level) == [(0x04, (254, 0))]  # clamped, instant
    assert color.options == [{"expect_reply": False}] and level.options == [{"expect_reply": False}]


async def test_an_animation_does_not_send_the_level_the_light_already_has():
    """A level command just after a color one disturbs the color glide on many bulbs."""
    z, _onoff, level, color = bulb()
    command = LightCommand(power=True, hex_color="#ff0000", brightness=180, transition_time=2, skip_same_level=True)

    await z.apply(command, is_on=True, known_level=180)
    assert len(sent(color)) == 1 and sent(level) == []  # only the color moves

    await z.apply(command, is_on=True, known_level=150)
    assert sent(level) == [(0x04, (180, 20))]  # the level changed: it is sent

    asked = LightCommand(power=True, hex_color="#00ff00", brightness=180, transition_time=2)
    await z.apply(asked, is_on=True, known_level=180)  # not an animation: always sent
    assert len(sent(level)) == 2

    await z.apply(command, is_on=False, known_level=180)  # a light that is off needs its level to come on
    assert len(sent(level)) == 3
