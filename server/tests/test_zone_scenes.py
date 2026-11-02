import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import init_db
from app.services.scenes import GUARD


async def make_room(client, devices=("bulb", "white", "socket")):
    return (await client.post("/rooms", json={"name": "Living room", "device_ids": list(devices)})).json()["id"]


def scene_body(room_id, palette, **extra):
    return {"name": "Warm", "target": {"type": "room", "id": room_id}, "palette": palette, **extra}


async def test_palette_is_spread_over_the_lights_of_the_room(client, fake):
    room = await make_room(client, ["bulb", "white"])
    palette = [{"hex_color": "#ff0000", "brightness": 200}, {"color_temp_kelvin": 2700}]
    created = await client.post("/scenes", json=scene_body(room, palette))
    assert created.status_code == 201 and created.json()["actions"] == []

    results = (await client.post(f"/scenes/{created.json()['id']}/apply")).json()["results"]
    assert results == {"bulb": True, "white": True}
    assert fake.lights("bulb")[-1].hex_color == "#ff0000"
    assert fake.lights("bulb")[-1].brightness == 200
    assert fake.lights("white")[-1].color_temp_kelvin == 2700


async def test_colors_are_limited_to_what_the_light_supports(client, fake):
    room = await make_room(client, ["white", "socket"])
    scene = await client.post("/scenes", json=scene_body(room, [{"hex_color": "#00ff00", "brightness": 90}]))
    await client.post(f"/scenes/{scene.json()['id']}/apply")

    white = fake.lights("white")[-1]  # a white-only bulb keeps the brightness, not the color
    assert white.hex_color is None and white.brightness == 90 and white.power is True
    assert fake.lights("socket") == []  # a socket has no color: it is left alone


async def test_assignments_place_a_light_on_a_given_color(client, fake):
    room = await make_room(client, ["bulb", "white"])
    palette = [{"hex_color": "#111111"}, {"hex_color": "#222222"}]
    body = scene_body(room, palette, assignments={"bulb": 1})
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    await client.post(f"/scenes/{scene_id}/apply")
    assert fake.lights("bulb")[-1].hex_color == "#222222"


async def test_scene_follows_the_group_when_it_changes(client, fake):
    group = (await client.post("/groups", json={"name": "Spots", "device_ids": ["bulb"]})).json()
    body = {"name": "Spots red", "target": {"type": "group", "id": group["id"]}, "palette": [{"hex_color": "#ff0000"}]}
    scene_id = (await client.post("/scenes", json=body)).json()["id"]

    await client.put(f"/groups/{group['id']}", json={"name": "Spots", "device_ids": ["bulb", "white"]})
    results = (await client.post(f"/scenes/{scene_id}/apply")).json()["results"]
    assert set(results) == {"bulb", "white"}


async def test_fade_applies_to_the_lights_that_change(client, fake):
    room = await make_room(client, ["bulb"])
    scene_id = (await client.post("/scenes", json=scene_body(room, [{"hex_color": "#ff0000"}], speed="medium"))).json()[
        "id"
    ]
    await client.post(f"/scenes/{scene_id}/apply")
    assert fake.lights("bulb")[-1].transition_time == 6  # the medium speed


async def test_scene_validation(client):
    room = await make_room(client)
    assert (await client.post("/scenes", json=scene_body(room, []))).status_code == 422
    assert (
        await client.post("/scenes", json=scene_body(room, [{"hex_color": "#ff0000", "color_temp_kelvin": 3000}]))
    ).status_code == 422
    assert (
        await client.post("/scenes", json=scene_body(room, [{"hex_color": "#ff0000"}], assignments={"bulb": 4}))
    ).status_code == 422
    assert (await client.post("/scenes", json={"name": "x", "palette": [{"hex_color": "#ff0000"}]})).status_code == 422
    mixed = scene_body(room, [{"hex_color": "#ff0000"}], actions=[{"device_id": "bulb", "power": True}])
    assert (await client.post("/scenes", json=mixed)).status_code == 422
    assert (await client.post("/scenes", json=scene_body(999, [{"hex_color": "#ff0000"}]))).status_code == 404


async def test_old_database_gets_the_new_scene_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE scenes (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL UNIQUE, actions JSON NOT NULL)")
        )
        await connection.execute(text("INSERT INTO scenes (name, actions) VALUES ('Old', '[]')"))
    await init_db(engine)
    async with engine.connect() as connection:
        row = (await connection.execute(text("SELECT name, target, palette, fade FROM scenes"))).one()
    assert tuple(row) == ("Old", None, None, 0)
    await engine.dispose()


async def test_a_socket_is_left_alone_unless_the_scene_says_otherwise(client, fake):
    room = await make_room(client, ["bulb", "socket"])
    scene_id = (await client.post("/scenes", json=scene_body(room, [{"hex_color": "#ff0000"}]))).json()["id"]
    results = (await client.post(f"/scenes/{scene_id}/apply")).json()["results"]
    assert results == {"bulb": True}
    assert fake.lights("socket") == []  # a kettle behind a socket must not switch on by itself


async def test_a_socket_can_be_switched_on_or_off_by_the_scene(client, fake):
    room = await make_room(client, ["bulb", "socket"])
    body = scene_body(room, [{"hex_color": "#ff0000"}], switches={"socket": True})
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    results = (await client.post(f"/scenes/{scene_id}/apply")).json()["results"]
    assert results == {"bulb": True, "socket": True}
    assert fake.lights("socket")[-1].power is True

    await client.put(f"/scenes/{scene_id}", json={**body, "switches": {"socket": False}})
    await client.post(f"/scenes/{scene_id}/apply")
    assert fake.lights("socket")[-1].power is False


async def test_a_light_listed_in_switches_does_not_take_a_color(client, fake):
    room = await make_room(client, ["bulb", "white"])
    palette = [{"hex_color": "#111111"}, {"hex_color": "#222222"}]
    body = scene_body(room, palette, switches={"bulb": False})
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    await client.post(f"/scenes/{scene_id}/apply")
    assert fake.lights("bulb")[-1].power is False and fake.lights("bulb")[-1].hex_color is None
    assert fake.lights("white")[-1].power is True  # the white bulb is now light 0 of the palette


async def test_switches_need_a_target(client):
    body = {"name": "x", "actions": [{"device_id": "bulb", "power": True}], "switches": {"socket": True}}
    assert (await client.post("/scenes", json=body)).status_code == 422


async def test_brightness_then_color_when_a_lit_light_changes_both(client, fake, container):
    """Two glide commands one after the other: the lamp ends the first at once (the color would jump)."""
    waits: list[float] = []

    async def record(seconds):
        waits.append(seconds)

    container.scenes._sleep = record
    await client.patch("/devices/bulb/light", json={"power": True, "brightness": 100})
    room = await make_room(client, ["bulb"])
    body = scene_body(room, [{"hex_color": "#ff0000", "brightness": 200}], speed="medium")  # 6 s
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    await client.post(f"/scenes/{scene_id}/apply")

    level, color = fake.lights("bulb")[-2:]
    assert level.brightness == 200 and level.hex_color is None and level.transition_time == 3.0
    assert color.hex_color == "#ff0000" and color.brightness is None
    assert color.transition_time == pytest.approx(3.0 - GUARD)  # the color glides once the brightness is done
    assert waits == [pytest.approx(3.0 + GUARD)]


async def test_one_command_when_only_the_color_changes(client, fake, container):
    await client.patch("/devices/bulb/light", json={"power": True, "brightness": 200})
    room = await make_room(client, ["bulb"])
    body = scene_body(room, [{"hex_color": "#ff0000", "brightness": 200}], speed="medium")
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    before = len(fake.lights("bulb"))
    await client.post(f"/scenes/{scene_id}/apply")

    (only,) = fake.lights("bulb")[before:]
    assert only.hex_color == "#ff0000" and only.brightness == 200 and only.transition_time == 6.0
