import asyncio

import pytest

from app.services.sequences import LEAD


async def make_scene(client, name, color):
    body = {"name": name, "actions": [{"device_id": "bulb", "power": True, "hex_color": color, "transition_time": 1}]}
    return (await client.post("/scenes", json=body)).json()["id"]


async def wait_for(condition, attempts=400):
    for _ in range(attempts):
        if condition():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("condition never became true")


def fast_sleep(container):
    """Replace the real waiting by a recorder, so tests do not last seconds."""
    waits: list[float] = []
    now = [0.0]

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds
        await asyncio.sleep(0)

    container.sequences._sleep = sleep
    container.sequences._clock = lambda: now[0]
    return waits


async def three_scenes(client):
    return [await make_scene(client, n, c) for n, c in (("Red", "#ff0000"), ("Green", "#00ff00"), ("Blue", "#0000ff"))]


async def test_validation_and_unknown_scene(client):
    scene_id = (await three_scenes(client))[0]
    assert (await client.post("/sequences", json={"name": "x", "steps": []})).status_code == 422
    bad_duration = {"name": "x", "steps": [{"scene_id": scene_id, "duration": 0}]}
    assert (await client.post("/sequences", json=bad_duration)).status_code == 422
    unknown = {"name": "x", "steps": [{"scene_id": 999, "duration": 2}]}
    assert (await client.post("/sequences", json=unknown)).status_code == 404


async def test_loop_plays_scenes_in_order_with_their_durations(client, container, fake):
    waits = fast_sleep(container)
    red, green, blue = await three_scenes(client)
    steps = [{"scene_id": red, "duration": 2}, {"scene_id": green, "duration": 5}, {"scene_id": blue, "duration": 10}]
    created = await client.post("/sequences", json={"name": "Party", "steps": steps})
    assert created.status_code == 201 and created.json()["loop"] is True

    await wait_for(lambda: len(fake.lights("bulb")) >= 5)
    colors = [c.hex_color for c in fake.lights("bulb")[:5]]
    assert colors == ["#ff0000", "#00ff00", "#0000ff", "#ff0000", "#00ff00"]  # loops back to the first scene
    # steps follow a timeline and are sent LEAD early: the first wait is shortened, the next ones are exact
    assert waits[:4] == pytest.approx([2 - LEAD, 5, 10, 2])
    # the fade lasts as long as the step: the color is reached when the duration ends
    assert [c.transition_time for c in fake.lights("bulb")[:4]] == [2, 5, 10, 2]

    sequence_id = created.json()["id"]
    assert (await client.get(f"/sequences/{sequence_id}")).json()["running"] is True
    await client.put(f"/sequences/{sequence_id}", json={"name": "Party", "steps": steps, "enabled": False})
    assert (await client.get(f"/sequences/{sequence_id}")).json()["running"] is False
    count = len(fake.lights("bulb"))
    await asyncio.sleep(0.01)
    assert len(fake.lights("bulb")) == count  # disabling stops it


async def test_without_loop_it_runs_once_and_disables_itself(client, container, fake):
    fast_sleep(container)
    red, green, _ = await three_scenes(client)
    steps = [{"scene_id": red, "duration": 1}, {"scene_id": green, "duration": 1}]
    sequence_id = (await client.post("/sequences", json={"name": "Once", "steps": steps, "loop": False})).json()["id"]

    await wait_for(lambda: container.sequences._tasks[sequence_id].done())
    assert [c.hex_color for c in fake.lights("bulb")] == ["#ff0000", "#00ff00"]
    assert (await client.get(f"/sequences/{sequence_id}")).json()["enabled"] is False


async def test_disabled_sequence_does_not_start_and_delete_stops_it(client, container, fake):
    fast_sleep(container)
    red = (await three_scenes(client))[0]
    steps = [{"scene_id": red, "duration": 3}]
    idle = (await client.post("/sequences", json={"name": "Idle", "steps": steps, "enabled": False})).json()
    assert idle["running"] is False and fake.lights("bulb") == []

    running = (await client.post("/sequences", json={"name": "Run", "steps": steps})).json()
    await wait_for(lambda: len(fake.lights("bulb")) >= 1)
    assert (await client.delete(f"/sequences/{running['id']}")).status_code == 204
    count = len(fake.lights("bulb"))
    await asyncio.sleep(0.01)
    assert len(fake.lights("bulb")) == count
    assert (await client.get(f"/sequences/{running['id']}")).status_code == 404


async def test_a_deleted_scene_is_skipped(client, container, fake):
    fast_sleep(container)
    red, green, _ = await three_scenes(client)
    steps = [{"scene_id": red, "duration": 1}, {"scene_id": green, "duration": 1}]
    await client.post("/sequences", json={"name": "Skip", "steps": steps, "enabled": False})
    sequence = (await client.get("/sequences")).json()[0]
    await client.delete(f"/scenes/{red}")
    await client.put(f"/sequences/{sequence['id']}", json={"name": "Skip", "steps": steps[1:], "loop": False})
    await wait_for(lambda: len(fake.lights("bulb")) >= 1)
    assert fake.lights("bulb")[0].hex_color == "#00ff00"


async def test_a_step_without_fade_keeps_the_fade_of_its_scene(client, container, fake):
    fast_sleep(container)
    red = (await three_scenes(client))[0]  # its action fades over 1 s
    steps = [{"scene_id": red, "duration": 7, "fade": False}]
    await client.post("/sequences", json={"name": "Snap", "steps": steps, "loop": False})
    await wait_for(lambda: len(fake.lights("bulb")) >= 1)
    assert fake.lights("bulb")[0].transition_time == 1


async def test_fade_does_not_apply_to_a_light_turned_off(client, container, fake):
    fast_sleep(container)
    body = {"name": "Night", "actions": [{"device_id": "bulb", "power": False}]}
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    steps = [{"scene_id": scene_id, "duration": 5}]
    await client.post("/sequences", json={"name": "Off", "steps": steps, "loop": False})
    await wait_for(lambda: len(fake.lights("bulb")) >= 1)
    assert fake.lights("bulb")[0].transition_time == 0
