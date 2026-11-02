import asyncio
import itertools

import pytest

from app.core.speeds import MIN_GLIDE, SPEED_SECONDS
from app.schemas.scene import SceneOut
from app.services.scenes import GUARD
from tests.conftest import make_device


class Ticker:
    """Replaces the sleep of the scene service: lets `ticks` steps happen, then waits for ever."""

    def __init__(self, ticks: int) -> None:
        self.ticks = ticks
        self.now = 1000.0
        self.delays: list[float] = []
        self.done = asyncio.Event()
        self._forever = asyncio.Event()

    def clock(self) -> float:
        return self.now

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)
        self.now += delay
        if len(self.delays) >= self.ticks:
            self.done.set()
            await self._forever.wait()
        await asyncio.sleep(0)


async def make_scene(client, devices=("bulb", "white"), **extra):
    room = (await client.post("/rooms", json={"name": "Living room", "device_ids": list(devices)})).json()["id"]
    body = {
        "name": "Loop",
        "target": {"type": "room", "id": room},
        "palette": [{"hex_color": "#ff0000"}, {"hex_color": "#00ff00"}, {"hex_color": "#0000ff"}],
        "animated": True,
        "speed": "fast",  # 2 s: a glide in one piece (the slower ones are cut in steps)
        **extra,
    }
    return (await client.post("/scenes", json=body)).json()


@pytest.fixture
def ticker(container):
    ticker = Ticker(ticks=3)
    container.scenes._sleep = ticker
    container.scenes._clock = ticker.clock
    return ticker


@pytest.fixture
def two_color_bulbs(fake):
    fake.devices["bulb2"] = make_device("bulb2", "Second bulb", "BULB", ["on_off", "brightness", "color"])


async def test_lights_step_through_the_palette_on_a_timeline(client, fake, ticker):
    scene = await make_scene(client, devices=["bulb"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)

    assert [c.hex_color for c in fake.lights("bulb")] == ["#ff0000", "#00ff00", "#0000ff"][: len(fake.lights("bulb"))]
    # the glide fills the slot of a color but for GUARD: the lamp has finished it when the next command comes
    commands = fake.lights("bulb")
    assert commands[0].transition_time == SPEED_SECONDS["fast"]  # the start
    assert all(c.transition_time == pytest.approx(2.0 - GUARD) for c in commands[1:])
    # and each command goes out when the slot ends, not before
    assert ticker.delays == pytest.approx([2.0] * len(ticker.delays))


async def test_lights_are_out_of_phase(client, fake, ticker, two_color_bulbs):
    scene = await make_scene(client, devices=["bulb", "bulb2"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)

    assert fake.lights("bulb")[0].hex_color == "#ff0000"  # light 0 starts on color 0
    assert fake.lights("bulb2")[0].hex_color == "#00ff00"  # light 1 on color 1
    assert fake.lights("bulb")[1].hex_color == "#00ff00"  # one step later: light 0 moved on
    assert fake.lights("bulb2")[1].hex_color == "#0000ff"


async def test_a_light_can_be_placed_on_a_color(client, fake, ticker, two_color_bulbs):
    scene = await make_scene(client, devices=["bulb", "bulb2"], assignments={"bulb2": 2})
    await client.post(f"/scenes/{scene['id']}/apply")
    assert fake.lights("bulb2")[0].hex_color == "#0000ff"


async def test_state_running_and_stop(client, fake, ticker):
    scene = await make_scene(client)
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False
    await client.post(f"/scenes/{scene['id']}/apply")
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is True

    stopped = await client.post(f"/scenes/{scene['id']}/stop")
    assert stopped.json()["info"] == "Animation stopped"
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False
    assert (await client.post(f"/scenes/{scene['id']}/stop")).json()["info"] == "No animation was running"


async def test_a_manual_command_on_one_of_its_lights_stops_it(client, fake, ticker):
    scene = await make_scene(client)
    await client.post(f"/scenes/{scene['id']}/apply")
    await client.patch("/devices/bulb/light", json={"power": False})
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False


async def test_a_command_on_another_light_leaves_it_running(client, fake, ticker):
    scene = await make_scene(client, devices=["bulb"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await client.patch("/devices/white/light", json={"power": False})
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is True


async def test_applying_another_scene_on_the_same_lights_stops_it(client, fake, ticker):
    scene = await make_scene(client)
    await client.post(f"/scenes/{scene['id']}/apply")
    plain = await client.post("/scenes", json={"name": "Plain", "actions": [{"device_id": "bulb", "power": True}]})
    await client.post(f"/scenes/{plain.json()['id']}/apply")
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False


async def test_deleting_a_scene_stops_its_animation(client, fake, ticker, container):
    scene = await make_scene(client)
    await client.post(f"/scenes/{scene['id']}/apply")
    await client.delete(f"/scenes/{scene['id']}")
    assert container.scenes._tasks == {}


async def test_running_scene_is_resumed_after_a_restart(client, fake, ticker, container):
    scene = await make_scene(client)
    await client.post(f"/scenes/{scene['id']}/apply")
    await container.scenes.shutdown()  # what a restart does: tasks end, the scene stays marked as running
    assert container.scenes._tasks == {}

    await container.scenes.restore()
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is True


async def test_animated_scene_validation(client):
    room = (await client.post("/rooms", json={"name": "R", "device_ids": ["bulb"]})).json()["id"]
    base = {"name": "x", "target": {"type": "room", "id": room}, "animated": True}
    one_color = {**base, "palette": [{"hex_color": "#ff0000"}]}
    assert (await client.post("/scenes", json=one_color)).status_code == 422
    two = [{"hex_color": "#ff0000"}, {"hex_color": "#00ff00"}]
    assert (await client.post("/scenes", json={**base, "palette": two})).status_code == 201
    assert (await client.post("/scenes", json={**base, "palette": two, "speed": "turbo"})).status_code == 422
    assert (await client.post("/scenes", json={**base, "palette": two, "speed": 0.5})).status_code == 422


async def test_sockets_are_switched_once_when_the_animation_starts(client, fake, ticker):
    scene = await make_scene(client, devices=["bulb", "socket"], switches={"socket": True})
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)
    assert [c.power for c in fake.lights("socket")] == [True]  # once, not at every step
    assert len(fake.lights("bulb")) > 1  # while the bulb loops

    await client.patch("/devices/socket/light", json={"power": False})
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False  # a command on it stops the loop


async def test_a_socket_not_listed_is_not_touched_by_the_loop(client, fake, ticker):
    scene = await make_scene(client, devices=["bulb", "socket"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)
    assert fake.lights("socket") == []


async def test_a_glide_between_two_far_colors_is_cut_in_steps_and_ends_on_the_color(client, fake, ticker):
    ticker.ticks = 7
    palette = [{"hex_color": "#0000ff", "brightness": 254}, {"hex_color": "#ffffcc", "brightness": 254}]
    scene = await make_scene(client, devices=["bulb"], palette=palette, speed="slow")
    seconds = SPEED_SECONDS["slow"]
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)

    commands = fake.lights("bulb")
    assert commands[0].hex_color == "#0000ff"  # the start, on the first color
    parts = round(seconds / commands[1].transition_time)  # the glide of the first change, cut in this many steps
    assert parts >= 3  # not one straight line through the color space
    glide = commands[1 : parts + 1]
    assert glide[-1].hex_color == "#ffffcc"  # it ends exactly on the color of the palette
    assert all(c.transition_time == pytest.approx(seconds / parts - GUARD) for c in glide)
    assert all(c.transition_time >= MIN_GLIDE for c in glide)  # never a glide the radio cannot follow
    assert ticker.delays[1:parts] == pytest.approx([seconds / parts] * (parts - 1))  # each part starts as one ends


async def test_a_lamp_is_never_sent_anything_while_it_is_still_gliding(client, fake, ticker):
    arrivals: list[tuple[float, float]] = []
    original = fake.set_light

    async def slow(device_id, command):
        ticker.now += 0.6  # a slow radio: it takes 0.6 s to deliver a command
        arrivals.append((ticker.now, command.transition_time))
        return await original(device_id, command)

    fake.set_light = slow
    ticker.ticks = 6
    scene = await make_scene(client, devices=["bulb"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)

    assert len(arrivals) >= 4
    for (before, glide), (after, _) in itertools.pairwise(arrivals):
        assert after - before >= glide  # the next command reaches the lamp once the glide is over


async def test_a_slow_radio_does_not_make_the_timeline_burst(client, fake, ticker):
    original = fake.set_light

    async def very_slow(device_id, command):
        ticker.now += 9  # longer than a whole step
        return await original(device_id, command)

    fake.set_light = very_slow
    scene = await make_scene(client, devices=["bulb"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)
    assert all(delay >= 0 for delay in ticker.delays)  # late, so the steps follow one after the other, no burst


async def test_the_whole_palette_shares_one_brightness(client):
    room = (await client.post("/rooms", json={"name": "R", "device_ids": ["bulb"]})).json()["id"]
    palette = [
        {"hex_color": "#ff0000", "brightness": 120},
        {"hex_color": "#00ff00", "brightness": 254},
        {"hex_color": "#0000ff"},
    ]
    body = {"name": "x", "target": {"type": "room", "id": room}, "palette": palette, "animated": True}
    scene = (await client.post("/scenes", json=body)).json()
    assert [c.get("brightness") for c in scene["palette"]] == [120, 120, 120]  # the first color sets it

    static = {**body, "name": "y", "animated": False}
    kept = (await client.post("/scenes", json=static)).json()
    assert [c.get("brightness") for c in kept["palette"]] == [120, 254, None]  # only animations are bound


async def test_the_level_is_not_sent_again_while_it_does_not_change(client, fake, ticker):
    ticker.ticks = 5
    scene = await make_scene(client, devices=["bulb"])
    await client.post(f"/scenes/{scene['id']}/apply")
    await asyncio.wait_for(ticker.done.wait(), 2)

    commands = fake.lights("bulb")
    assert commands[0].skip_same_level is False  # the start sets the level
    assert all(c.skip_same_level for c in commands[1:])  # the loop only moves the color


async def test_there_are_three_speeds_and_no_other_time(client):
    room = (await client.post("/rooms", json={"name": "R", "device_ids": ["bulb"]})).json()["id"]
    palette = [{"hex_color": "#ff0000"}, {"hex_color": "#00ff00"}]
    base = {"target": {"type": "room", "id": room}, "palette": palette, "animated": True}

    for index, (speed, seconds) in enumerate(SPEED_SECONDS.items()):
        scene = (await client.post("/scenes", json={**base, "name": speed, "speed": speed})).json()
        # each color lasts as long as the glide to it: the lights glide all the time
        assert (scene["speed"], scene["fade"], scene["duration"]) == (speed, seconds, seconds), index

    # the seconds of an older client are ignored: the only times are the three speeds
    old = {**base, "name": "old", "fade": 0.1, "duration": 0.5}
    scene = (await client.post("/scenes", json=old)).json()
    assert (scene["speed"], scene["fade"], scene["duration"]) == ("medium", 6.0, 6.0)


def test_an_older_animated_scene_never_glides_for_less_than_the_minimum():
    saved = {
        "id": 1,
        "name": "old",
        "actions": [],
        "target": {"type": "room", "id": 1},
        "palette": [{"hex_color": "#ff0000"}, {"hex_color": "#00ff00"}],
        "animated": True,
        "duration": 1.5,  # saved before the three speeds
        "fade": 0.5,
    }
    scene = SceneOut(**saved)
    assert scene.speed == "fast"  # the closest speed, for the editor
    from app.services.scenes import SceneService

    assert SceneService._timing(scene) == (MIN_GLIDE, MIN_GLIDE)  # a glide the whole time, never shorter
    still = SceneOut(**{**saved, "animated": False, "fade": 0})
    assert SceneService._timing(still) == (1.5, 0)  # a plain scene is applied as saved


async def test_stop_cancels_a_scene_still_waiting_for_a_lamp(client, fake, container):
    """The first step is stuck in the radio queue: stop must end it, and a new start must not leave a second
    loop behind."""
    scene = await make_scene(client)
    release = asyncio.Event()
    original = fake.set_light

    async def stuck(device_id, command):
        await release.wait()
        return await original(device_id, command)

    fake.set_light = stuck
    start = asyncio.ensure_future(client.post(f"/scenes/{scene['id']}/apply"))
    await asyncio.sleep(0.05)
    assert container.scenes._tasks  # registered although nothing was acknowledged yet

    assert (await client.post(f"/scenes/{scene['id']}/stop")).status_code == 200
    assert container.scenes._tasks == {}
    assert (await start).status_code == 200
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False

    fake.set_light = original
    await client.post(f"/scenes/{scene['id']}/apply")
    await client.post(f"/scenes/{scene['id']}/apply")  # starting twice keeps a single loop
    assert len(container.scenes._tasks) == 1
    await client.post(f"/scenes/{scene['id']}/stop")
    assert container.scenes._tasks == {}


async def test_a_request_is_answered_at_once_even_if_a_lamp_never_answers(client, fake, container, monkeypatch):
    """Applying a scene is not held by a lamp that is lost: the answer comes in time, the animation starts
    anyway, and stop still works."""
    from app.services import scenes as scenes_module

    monkeypatch.setattr(scenes_module, "START_WAIT", 0.05)
    monkeypatch.setattr(scenes_module, "STEP_TIMEOUT", 0.2)
    scene = await make_scene(client)
    never = asyncio.Event()

    async def lost(device_id, command):
        await never.wait()
        return True

    fake.set_light = lost
    started = asyncio.get_running_loop().time()
    response = await client.post(f"/scenes/{scene['id']}/apply")
    assert response.status_code == 200
    assert response.json()["results"] == {}
    assert asyncio.get_running_loop().time() - started < 1

    async def running():  # the first step gave up on the lamp: the animation is running
        while scene["id"] not in container.scenes._lights_of:  # noqa: ASYNC110
            await asyncio.sleep(0.02)

    await asyncio.wait_for(running(), 5)
    assert (await client.post(f"/scenes/{scene['id']}/stop")).status_code == 200
    assert container.scenes._tasks == {}


async def test_a_failed_start_leaves_nothing_behind(client, fake, container):
    """A start that fails is not a running scene, and deleting a scene forgets everything about it."""
    scene = await make_scene(client)
    original = fake.set_light

    async def broken(device_id, command):
        raise RuntimeError("radio")

    fake.set_light = broken
    with pytest.raises(RuntimeError):
        await container.scenes.apply(scene["id"])
    assert container.scenes._tasks == {}
    assert not container.scenes._running(scene["id"])
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False

    fake.set_light = original
    await client.post(f"/scenes/{scene['id']}/apply")
    assert container.scenes._running(scene["id"])
    assert scene["id"] in container.scenes._locks
    assert (await client.delete(f"/scenes/{scene['id']}")).status_code == 204
    assert container.scenes._tasks == {}
    assert container.scenes._locks == {}
