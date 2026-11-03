async def test_list_devices(client):
    response = await client.get("/devices")
    assert response.status_code == 200
    ids = {d["id"] for d in response.json()["devices"]}
    assert ids == {"bulb", "white", "socket", "sensor", "button"}


async def test_get_device_and_unknown(client):
    assert (await client.get("/devices/bulb")).json()["type"] == "BULB"
    assert (await client.get("/devices/nope")).status_code == 404


async def test_rename_device_and_reset(client):
    renamed = await client.patch("/devices/socket", json={"name": "  Kitchen  "})
    assert renamed.json()["name"] == "Kitchen"
    listed = {d["id"]: d["name"] for d in (await client.get("/devices")).json()["devices"]}
    assert listed["socket"] == "Kitchen"

    reset = await client.patch("/devices/socket", json={"name": None})
    assert reset.json()["name"] == "Socket"


async def test_rename_unknown_device(client):
    assert (await client.patch("/devices/nope", json={"name": "x"})).status_code == 404


async def test_power_and_brightness(client, fake):
    response = await client.patch("/devices/bulb/light", json={"power": True, "brightness": 128})
    assert response.status_code == 200
    command = fake.lights("bulb")[-1]
    assert command.power is True and command.brightness == 128


async def test_color_hex_and_hue(client, fake):
    assert (await client.patch("/devices/bulb/light", json={"hex_color": "#ff0000"})).status_code == 200
    assert fake.lights("bulb")[-1].hex_color == "#ff0000"
    assert (await client.patch("/devices/bulb/light", json={"hue": 200, "saturation": 80})).status_code == 200
    assert fake.lights("bulb")[-1].hue == 200


async def test_white_light(client, fake):
    response = await client.patch("/devices/white/light", json={"color_temp_kelvin": 2700, "brightness": 200})
    assert response.status_code == 200
    assert fake.lights("white")[-1].color_temp_kelvin == 2700


async def test_color_refused_on_white_only_bulb(client, fake):
    response = await client.patch("/devices/white/light", json={"hex_color": "#00ff00"})
    assert response.status_code == 422
    assert "color" in response.json()["detail"]
    assert fake.lights("white") == []


async def test_light_command_on_a_sensor_is_refused(client):
    assert (await client.patch("/devices/sensor/light", json={"power": True})).status_code == 422


async def test_invalid_bodies(client):
    assert (await client.patch("/devices/bulb/light", json={})).status_code == 422
    assert (await client.patch("/devices/bulb/light", json={"hue": 10})).status_code == 422
    assert (
        await client.patch("/devices/bulb/light", json={"hue": 10, "saturation": 5, "color_temp_kelvin": 3000})
    ).status_code == 422
    assert (await client.patch("/devices/bulb/light", json={"brightness": 300})).status_code == 422
    assert (await client.patch("/devices/bulb/light", json={"hex_color": "red"})).status_code == 422
    assert (await client.patch("/devices/bulb/light", json={"power": True, "oops": 1})).status_code == 422


async def test_unreachable_device_returns_502(client, fake):
    fake.unreachable.add("bulb")
    response = await client.patch("/devices/bulb/light", json={"power": False})
    assert response.status_code == 502


async def test_unknown_device_light_returns_404(client):
    assert (await client.patch("/devices/nope/light", json={"power": True})).status_code == 404


async def test_toggle(client, fake):
    assert (await client.post("/devices/socket/toggle")).status_code == 200
    assert ("socket", "toggle", None) in fake.commands
    fake.unreachable.add("socket")
    assert (await client.post("/devices/socket/toggle")).status_code == 502


async def test_refresh_returns_sensor_reading(client, fake):
    response = await client.post("/devices/sensor/refresh")
    assert response.json()["state"]["temperature"] == 21.5
    assert ("sensor", "refresh", None) in fake.commands


async def test_discovery_and_coordinator_info(client, fake):
    assert (await client.post("/coordinator/discovery?seconds=45")).status_code == 200
    assert fake.permit_seconds == 45
    assert (await client.post("/coordinator/discovery?seconds=0")).status_code == 422
    assert (await client.get("/coordinator")).json()["coordinators"][0]["protocol"] == "fake"


async def test_remove_device_forgets_it_everywhere(client, fake):
    await client.patch("/devices/socket", json={"name": "Kettle"})
    room = (await client.post("/rooms", json={"name": "Kitchen", "device_ids": ["socket", "bulb"]})).json()
    group = (await client.post("/groups", json={"name": "Warm", "device_ids": ["socket", "white"]})).json()
    scene = {
        "name": "Evening",
        "target": {"type": "room", "id": room["id"]},
        "palette": [{"hex_color": "#ff8800"}],
        "assignments": {"socket": 0, "bulb": 0},
        "switches": {"socket": True, "white": False},
    }
    scene_id = (await client.post("/scenes", json=scene)).json()["id"]
    pressed = {"device_id": "button", "event": "on_off.toggle", "action": {"type": "toggle", "device_id": "socket"}}
    await client.put("/buttons", json=pressed)

    assert (await client.delete("/devices/socket")).status_code == 204

    assert fake.removed == ["socket"]
    assert (await client.get("/devices/socket")).status_code == 404
    assert "socket" not in [d["id"] for d in (await client.get("/devices")).json()["devices"]]
    assert (await client.get(f"/rooms/{room['id']}")).json()["device_ids"] == ["bulb"]
    assert (await client.get(f"/groups/{group['id']}")).json()["device_ids"] == ["white"]
    cleaned = (await client.get(f"/scenes/{scene_id}")).json()
    assert cleaned["assignments"] == {"bulb": 0} and cleaned["switches"] == {"white": False}
    assert (await client.get("/buttons")).json() == []  # it drove the removed socket


async def test_remove_device_drops_its_own_button_mappings(client):
    body = {"device_id": "button", "event": "on_off.toggle", "action": {"type": "toggle", "device_id": "socket"}}
    await client.put("/buttons", json=body)
    assert (await client.delete("/devices/button")).status_code == 204
    assert (await client.get("/buttons")).json() == []


async def test_remove_cleans_what_the_radio_no_longer_knows(client):
    await client.post("/rooms", json={"name": "Attic", "device_ids": ["ghost"]})
    assert (await client.delete("/devices/ghost")).status_code == 204
    rooms = (await client.get("/rooms")).json()
    assert [r["device_ids"] for r in rooms if r["name"] == "Attic"] == [[]]
