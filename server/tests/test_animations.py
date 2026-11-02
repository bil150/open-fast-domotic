import asyncio

from app.main import create_app
from app.schemas.animation import AnimationKey

KEYS = {
    "keys": [
        {"hue": 0, "saturation": 100, "brightness": 200, "transition_time": 1},
        {"hue": 120, "saturation": 100, "brightness": 200, "transition_time": 1},
    ]
}


async def test_animation_runs_and_stops(client, fake, container):
    assert (await client.put("/devices/bulb/animation", json=KEYS)).status_code == 200
    await asyncio.sleep(0.1)
    assert fake.lights("bulb")[0].hue == 0 and fake.lights("bulb")[0].power is True
    assert container.animations.running() == ["bulb"]

    assert (await client.delete("/devices/bulb/animation")).json()["info"] == "Animation stopped"
    assert container.animations.running() == []
    assert (await client.delete("/devices/bulb/animation")).json()["info"] == "No animation was running"


async def test_animation_steps_through_the_keys(client, fake):
    await client.put("/devices/bulb/animation", json=KEYS)
    await asyncio.sleep(1.3)
    assert [c.hue for c in fake.lights("bulb")][:2] == [0, 120]
    await client.delete("/devices/bulb/animation")


async def test_manual_command_stops_the_animation(client, fake, container):
    await client.put("/devices/bulb/animation", json=KEYS)
    await asyncio.sleep(0.05)
    await client.patch("/devices/bulb/light", json={"power": False})
    assert container.animations.running() == []


async def test_animation_validation(client):
    assert (await client.put("/devices/bulb/animation", json={"keys": []})).status_code == 422
    bad = {"keys": [{"hue": 400, "saturation": 100, "brightness": 10, "transition_time": 1}]}
    assert (await client.put("/devices/bulb/animation", json=bad)).status_code == 422
    assert (await client.put("/devices/ghost/animation", json=KEYS)).status_code == 404


async def test_animation_is_restored_after_restart(settings, fake):
    settings.restore_animations = True
    first = create_app(settings, [fake])
    async with first.router.lifespan_context(first):
        await first.state.container.animations.start("bulb", [AnimationKey(**KEYS["keys"][0])])
        assert first.state.container.animations.running() == ["bulb"]

    second = create_app(settings, [fake])
    async with second.router.lifespan_context(second):
        await asyncio.sleep(0.1)
        assert second.state.container.animations.running() == ["bulb"]
        await second.state.container.animations.stop("bulb")
