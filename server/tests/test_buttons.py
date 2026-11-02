from tests.conftest import button_event


async def test_mapping_crud(client):
    body = {"device_id": "button", "event": "on_off.toggle", "action": {"type": "toggle", "device_id": "socket"}}
    created = await client.put("/buttons", json=body)
    assert created.status_code == 200 and created.json()["action"]["type"] == "toggle"

    # same (device, event) replaces the action instead of adding one
    body["action"] = {"type": "power", "device_id": "socket", "state": False}
    await client.put("/buttons", json=body)
    mappings = (await client.get("/buttons?device_id=button")).json()
    assert len(mappings) == 1 and mappings[0]["action"]["state"] is False

    assert (await client.delete(f"/buttons/{mappings[0]['id']}")).status_code == 204
    assert (await client.delete("/buttons/999")).status_code == 404
    assert (await client.get("/buttons")).json() == []


async def test_mapping_validation(client):
    unknown = {"device_id": "ghost", "event": "x", "action": {"type": "toggle", "device_id": "socket"}}
    assert (await client.put("/buttons", json=unknown)).status_code == 404
    bad_type = {"device_id": "button", "event": "x", "action": {"type": "explode"}}
    assert (await client.put("/buttons", json=bad_type)).status_code == 422
    missing = {"device_id": "button", "event": "x", "action": {"type": "scene"}}
    assert (await client.put("/buttons", json=missing)).status_code == 422


async def test_button_runs_a_scene(client, fake):
    scene_id = (
        await client.post(
            "/scenes", json={"name": "S", "actions": [{"device_id": "bulb", "power": True, "brightness": 200}]}
        )
    ).json()["id"]
    await client.put(
        "/buttons",
        json={"device_id": "button", "event": "on_off.on", "action": {"type": "scene", "scene_id": scene_id}},
    )

    fake.emit(button_event("button", "on_off.on"))
    await _settle()
    assert fake.lights("bulb")[-1].brightness == 200


async def test_button_toggles_and_sets_power(client, fake):
    await client.put(
        "/buttons",
        json={"device_id": "button", "event": "on_off.toggle", "action": {"type": "toggle", "device_id": "socket"}},
    )
    await client.put(
        "/buttons",
        json={
            "device_id": "button",
            "event": "on_off.off",
            "action": {"type": "power", "device_id": "bulb", "state": False},
        },
    )

    fake.emit(button_event("button", "on_off.toggle"))
    fake.emit(button_event("button", "on_off.off"))
    await _settle()
    assert ("socket", "toggle", None) in fake.commands
    assert fake.lights("bulb")[-1].power is False


async def test_unmapped_event_and_broken_mapping_do_nothing(client, fake):
    fake.emit(button_event("button", "level.step"))
    await client.put(
        "/buttons", json={"device_id": "button", "event": "on_off.on", "action": {"type": "scene", "scene_id": 999}}
    )
    fake.emit(button_event("button", "on_off.on"))
    await _settle()
    assert fake.commands == []


async def _settle():
    import asyncio

    for _ in range(5):
        await asyncio.sleep(0.02)
