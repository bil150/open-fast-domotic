SCENE = {
    "name": "Evening",
    "actions": [
        {"device_id": "bulb", "power": True, "hex_color": "#ff8800", "brightness": 120, "transition_time": 2},
        {"device_id": "white", "power": True, "color_temp_kelvin": 2700},
        {"device_id": "socket", "power": False},
    ],
}


async def test_create_list_get_scene(client):
    created = await client.post("/scenes", json=SCENE)
    assert created.status_code == 201
    scene_id = created.json()["id"]
    assert [s["name"] for s in (await client.get("/scenes")).json()] == ["Evening"]
    assert (await client.get(f"/scenes/{scene_id}")).json()["actions"][0]["hex_color"] == "#ff8800"


async def test_duplicate_name_conflicts(client):
    await client.post("/scenes", json=SCENE)
    assert (await client.post("/scenes", json=SCENE)).status_code == 409


async def test_scene_validation(client):
    assert (await client.post("/scenes", json={"name": "x", "actions": []})).status_code == 422
    assert (await client.post("/scenes", json={"name": "x", "actions": [{"device_id": "bulb"}]})).status_code == 422


async def test_apply_scene_sends_every_action(client, fake):
    scene_id = (await client.post("/scenes", json=SCENE)).json()["id"]
    response = await client.post(f"/scenes/{scene_id}/apply")
    assert response.json()["results"] == {"bulb": True, "white": True, "socket": True}
    assert fake.lights("bulb")[-1].hex_color == "#ff8800"
    assert fake.lights("bulb")[-1].transition_time == 2
    assert fake.lights("white")[-1].color_temp_kelvin == 2700
    assert fake.lights("socket")[-1].power is False


async def test_apply_scene_reports_unreachable_and_unknown_devices(client, fake):
    fake.unreachable.add("white")
    body = {
        "name": "Mixed",
        "actions": [
            {"device_id": "white", "power": True},
            {"device_id": "ghost", "power": True},
            {"device_id": "bulb", "power": True},
        ],
    }
    scene_id = (await client.post("/scenes", json=body)).json()["id"]
    results = (await client.post(f"/scenes/{scene_id}/apply")).json()["results"]
    assert results == {"white": False, "ghost": False, "bulb": True}


async def test_update_and_delete_scene(client):
    scene_id = (await client.post("/scenes", json=SCENE)).json()["id"]
    updated = await client.put(
        f"/scenes/{scene_id}", json={"name": "Night", "actions": [{"device_id": "bulb", "power": False}]}
    )
    assert updated.json()["name"] == "Night" and len(updated.json()["actions"]) == 1
    assert (await client.delete(f"/scenes/{scene_id}")).status_code == 204
    assert (await client.get(f"/scenes/{scene_id}")).status_code == 404
    assert (await client.post(f"/scenes/{scene_id}/apply")).status_code == 404
    assert (await client.put("/scenes/999", json=SCENE)).status_code == 404
    assert (await client.delete("/scenes/999")).status_code == 404
