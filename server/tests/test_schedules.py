from datetime import datetime

from app.utils.cron import is_valid_cron, matches, next_run


async def make_scene(client, name="Wake up"):
    body = {"name": name, "actions": [{"device_id": "bulb", "power": True}]}
    return (await client.post("/scenes", json=body)).json()["id"]


def test_cron_helpers():
    assert is_valid_cron("30 7 * * 1-5")
    assert not is_valid_cron("30 7 * *")
    assert not is_valid_cron("0 30 7 * * 1")  # 6 fields: seconds are not supported
    assert not is_valid_cron("nope nope nope nope nope")
    assert matches("30 7 * * *", datetime(2026, 5, 4, 7, 30))
    assert not matches("30 7 * * *", datetime(2026, 5, 4, 7, 31))
    assert next_run("0 8 * * *", datetime(2026, 5, 4, 7, 0)) == "2026-05-04T08:00"
    assert next_run("bad") is None


async def test_create_and_list(client):
    scene_id = await make_scene(client)
    created = await client.post("/schedules", json={"name": "Morning", "cron": "30  7 * * 1-5", "scene_id": scene_id})
    assert created.status_code == 201
    body = created.json()
    assert body["cron"] == "30 7 * * 1-5" and body["enabled"] is True and body["next_run"]
    assert len((await client.get("/schedules")).json()) == 1


async def test_validation_and_unknown_scene(client):
    scene_id = await make_scene(client)
    assert (await client.post("/schedules", json={"name": "x", "cron": "bad", "scene_id": scene_id})).status_code == 422
    assert (
        await client.post("/schedules", json={"name": "x", "cron": "* * * * *", "scene_id": 999})
    ).status_code == 404


async def test_update_disable_and_delete(client):
    scene_id = await make_scene(client)
    schedule_id = (
        await client.post("/schedules", json={"name": "A", "cron": "0 6 * * *", "scene_id": scene_id})
    ).json()["id"]
    updated = await client.put(
        f"/schedules/{schedule_id}", json={"name": "A", "cron": "0 7 * * *", "scene_id": scene_id, "enabled": False}
    )
    assert updated.json()["cron"] == "0 7 * * *" and updated.json()["next_run"] is None
    assert (await client.delete(f"/schedules/{schedule_id}")).status_code == 204
    assert (await client.get(f"/schedules/{schedule_id}")).status_code == 404


async def test_deleting_a_scene_removes_its_schedules(client):
    scene_id = await make_scene(client)
    await client.post("/schedules", json={"name": "A", "cron": "0 6 * * *", "scene_id": scene_id})
    await client.delete(f"/scenes/{scene_id}")
    assert (await client.get("/schedules")).json() == []


async def test_tick_fires_matching_schedule_once_per_minute(client, container, fake):
    scene_id = await make_scene(client)
    await client.post("/schedules", json={"name": "Match", "cron": "30 7 * * *", "scene_id": scene_id})
    await client.post("/schedules", json={"name": "Other", "cron": "31 7 * * *", "scene_id": scene_id})
    await client.post("/schedules", json={"name": "Off", "cron": "30 7 * * *", "scene_id": scene_id, "enabled": False})

    moment = datetime(2026, 5, 4, 7, 30, 12)
    assert len(await container.scheduler.tick(moment)) == 1
    assert len(fake.lights("bulb")) == 1
    assert await container.scheduler.tick(moment.replace(second=40)) == []  # same minute: no second run
    assert len(fake.lights("bulb")) == 1

    schedules = {s["name"]: s for s in (await client.get("/schedules")).json()}
    assert schedules["Match"]["last_run"] == "2026-05-04T07:30"
    assert schedules["Other"]["last_run"] is None
    assert len(await container.scheduler.tick(datetime(2026, 5, 5, 7, 30))) == 1  # next day runs again
