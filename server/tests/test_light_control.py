async def make_room(client, devices=("bulb", "white", "socket")):
    return (await client.post("/rooms", json={"name": "Living room", "device_ids": list(devices)})).json()["id"]


async def test_switch_a_room_off_and_on_with_its_sockets(client, fake):
    room = await make_room(client)
    off = await client.patch(f"/rooms/{room}/light", json={"power": False})
    assert off.json()["results"] == {"bulb": True, "white": True, "socket": True}
    assert all(fake.lights(d)[-1].power is False for d in ("bulb", "white", "socket"))

    await client.patch(f"/rooms/{room}/light", json={"power": True})
    assert all(fake.lights(d)[-1].power is True for d in ("bulb", "white", "socket"))


async def test_same_order_on_a_group(client, fake):
    group = (await client.post("/groups", json={"name": "Spots", "device_ids": ["bulb", "socket"]})).json()["id"]
    results = (await client.patch(f"/groups/{group}/light", json={"power": False})).json()["results"]
    assert results == {"bulb": True, "socket": True}
    assert fake.lights("white") == []  # not in the group


async def test_brighter_and_dimmer_by_a_step_of_each_light(client, fake):
    room = await make_room(client)
    await client.patch("/devices/bulb/light", json={"brightness": 100})
    await client.patch("/devices/white/light", json={"brightness": 200})

    up = await client.patch(f"/rooms/{room}/light", json={"brightness_step": 10})
    assert set(up.json()["results"]) == {"bulb", "white"}  # a socket does not dim
    assert fake.lights("bulb")[-1].brightness == 125  # 10% of the range, each from its own level
    assert fake.lights("white")[-1].brightness == 225
    assert fake.lights("socket") == []

    await client.patch(f"/rooms/{room}/light", json={"brightness_step": -100})
    assert fake.lights("bulb")[-1].brightness == 1  # never switched off by dimming
    assert fake.lights("white")[-1].brightness == 1


async def test_brighter_is_capped(client, fake):
    room = await make_room(client, ["bulb"])
    await client.patch("/devices/bulb/light", json={"brightness": 250})
    await client.patch(f"/rooms/{room}/light", json={"brightness_step": 50})
    assert fake.lights("bulb")[-1].brightness == 254


async def test_brighter_switches_on_a_light_that_is_off_and_dimmer_leaves_it_off(client, fake):
    room = await make_room(client, ["bulb"])
    await client.patch("/devices/bulb/light", json={"power": False})

    assert (await client.patch(f"/rooms/{room}/light", json={"brightness_step": -20})).json()["results"] == {}
    up = await client.patch(f"/rooms/{room}/light", json={"brightness_step": 20})
    assert up.json()["results"] == {"bulb": True}
    assert fake.lights("bulb")[-1].power is True and fake.lights("bulb")[-1].brightness == 51


async def test_set_a_brightness_on_the_lights_that_dim(client, fake):
    room = await make_room(client)
    results = (await client.patch(f"/rooms/{room}/light", json={"brightness": 80})).json()["results"]
    assert set(results) == {"bulb", "white"}
    assert fake.lights("bulb")[-1].brightness == 80 and fake.lights("bulb")[-1].power is True


async def test_unreachable_lights_are_reported(client, fake):
    room = await make_room(client, ["bulb", "white"])
    fake.unreachable.add("white")
    results = (await client.patch(f"/rooms/{room}/light", json={"power": True})).json()["results"]
    assert results == {"bulb": True, "white": False}


async def test_a_device_removed_from_the_network_is_skipped(client):
    room = await make_room(client, ["bulb", "ghost"])
    results = (await client.patch(f"/rooms/{room}/light", json={"power": False})).json()["results"]
    assert results == {"bulb": True}


async def test_validation_and_unknown_zone(client):
    room = await make_room(client)
    assert (await client.patch(f"/rooms/{room}/light", json={})).status_code == 422
    both = {"brightness": 100, "brightness_step": 10}
    assert (await client.patch(f"/rooms/{room}/light", json=both)).status_code == 422
    assert (await client.patch(f"/rooms/{room}/light", json={"brightness_step": 500})).status_code == 422
    assert (await client.patch("/rooms/999/light", json={"power": True})).status_code == 404
    assert (await client.patch("/groups/999/light", json={"power": True})).status_code == 404


async def test_the_whole_home_on_and_off(client, fake):
    off = await client.patch("/lights", json={"power": False})
    assert off.json()["results"] == {"bulb": True, "white": True, "socket": True}  # no sensor, no button
    assert all(fake.lights(d)[-1].power is False for d in ("bulb", "white", "socket"))

    on = await client.patch("/lights", json={"power": True})
    assert set(on.json()["results"]) == {"bulb", "white", "socket"}


async def test_the_whole_home_brighter(client, fake):
    await client.patch("/devices/bulb/light", json={"brightness": 100})
    results = (await client.patch("/lights", json={"brightness_step": 10})).json()["results"]
    assert set(results) == {"bulb", "white"}
    assert fake.lights("bulb")[-1].brightness == 125


async def test_an_order_on_a_room_stops_the_animated_scene_on_its_lights(client, fake):
    room = await make_room(client, ["bulb", "white"])
    body = {
        "name": "Loop",
        "target": {"type": "room", "id": room},
        "palette": [{"hex_color": "#ff0000"}, {"hex_color": "#00ff00"}],
        "animated": True,
    }
    scene = (await client.post("/scenes", json=body)).json()
    await client.post(f"/scenes/{scene['id']}/apply")
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is True

    await client.patch(f"/rooms/{room}/light", json={"power": False})
    assert (await client.get(f"/scenes/{scene['id']}")).json()["running"] is False
