async def test_room_crud(client):
    created = await client.post("/rooms", json={"name": "Living room", "device_ids": ["bulb", "white", "bulb"]})
    assert created.status_code == 201
    room = created.json()
    assert room["device_ids"] == ["bulb", "white"]  # duplicates dropped, order kept

    assert [r["name"] for r in (await client.get("/rooms")).json()] == ["Living room"]
    assert (await client.get(f"/rooms/{room['id']}")).json()["name"] == "Living room"

    updated = await client.put(f"/rooms/{room['id']}", json={"name": "Salon", "device_ids": ["bulb"]})
    assert updated.json() == {"id": room["id"], "name": "Salon", "device_ids": ["bulb"]}

    assert (await client.delete(f"/rooms/{room['id']}")).status_code == 204
    assert (await client.get(f"/rooms/{room['id']}")).status_code == 404


async def test_names_are_unique_and_validated(client):
    await client.post("/rooms", json={"name": "Kitchen", "device_ids": []})
    assert (await client.post("/rooms", json={"name": "Kitchen", "device_ids": []})).status_code == 409
    assert (await client.post("/groups", json={"name": "", "device_ids": []})).status_code == 422


async def test_a_device_belongs_to_one_room_only(client):
    first = (await client.post("/rooms", json={"name": "A", "device_ids": ["bulb", "white"]})).json()
    second = (await client.post("/rooms", json={"name": "B", "device_ids": ["white"]})).json()

    assert (await client.get(f"/rooms/{first['id']}")).json()["device_ids"] == ["bulb"]
    assert (await client.get(f"/rooms/{second['id']}")).json()["device_ids"] == ["white"]

    # moving a device through an update takes it away from its previous room as well
    await client.put(f"/rooms/{first['id']}", json={"name": "A", "device_ids": ["bulb", "white"]})
    assert (await client.get(f"/rooms/{second['id']}")).json()["device_ids"] == []


async def test_a_device_can_be_in_several_groups(client):
    a = (await client.post("/groups", json={"name": "Spots", "device_ids": ["bulb", "white"]})).json()
    b = (await client.post("/groups", json={"name": "Ambient", "device_ids": ["white"]})).json()

    assert (await client.get(f"/groups/{a['id']}")).json()["device_ids"] == ["bulb", "white"]
    assert (await client.get(f"/groups/{b['id']}")).json()["device_ids"] == ["white"]
    assert (await client.get("/groups/999")).status_code == 404
