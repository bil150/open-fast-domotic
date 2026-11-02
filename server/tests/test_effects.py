import asyncio
import random

import pytest

from app.main import create_app
from app.services.effects import EFFECTS, next_step


@pytest.mark.parametrize("effect", EFFECTS)
def test_every_step_stays_within_the_peak_and_is_warm(effect):
    rng = random.Random(1)
    for _ in range(500):
        command, wait = next_step(effect, 120, rng)
        assert 1 <= command.brightness <= 120
        assert command.power is True and 0 <= command.hue <= 40  # reds to oranges
        assert wait >= command.transition_time > 0


def test_a_fire_flickers_more_than_a_candle():
    def spread(effect):
        rng = random.Random(2)
        levels = [next_step(effect, 255, rng)[0].brightness for _ in range(500)]
        return max(levels) - min(levels)

    assert spread("fire") > 0 and spread("candle") > 0


def test_unknown_effect_is_refused():
    with pytest.raises(ValueError, match="Unknown effect"):
        next_step("disco", 255, random.Random())


async def test_effect_runs_reports_and_stops(client, fake, container):
    assert (await client.get("/devices/bulb/effect")).json() == {"effect": None}
    response = await client.put("/devices/bulb/effect", json={"effect": "fire", "brightness": 100})
    assert response.json() == {"effect": "fire"}
    await asyncio.sleep(0.1)
    assert fake.lights("bulb") and fake.lights("bulb")[0].brightness <= 100
    assert (await client.get("/devices/bulb/effect")).json() == {"effect": "fire"}

    await client.delete("/devices/bulb/animation")
    assert (await client.get("/devices/bulb/effect")).json() == {"effect": None}
    assert container.animations.running() == []


async def test_manual_command_stops_the_effect(client, container):
    await client.put("/devices/bulb/effect", json={"effect": "candle"})
    await asyncio.sleep(0.05)
    await client.patch("/devices/bulb/light", json={"power": False})
    assert (await client.get("/devices/bulb/effect")).json() == {"effect": None}


async def test_effect_validation(client):
    assert (await client.put("/devices/bulb/effect", json={"effect": "disco"})).status_code == 422
    assert (await client.put("/devices/socket/effect", json={"effect": "fire"})).status_code == 422  # not a bulb
    assert (await client.put("/devices/ghost/effect", json={"effect": "fire"})).status_code == 404


async def test_effect_is_restored_after_restart(settings, fake):
    settings.restore_animations = True
    first = create_app(settings, [fake])
    async with first.router.lifespan_context(first):
        await first.state.container.animations.start_effect("bulb", "candle", 150)

    second = create_app(settings, [fake])
    async with second.router.lifespan_context(second):
        await asyncio.sleep(0.1)
        assert second.state.container.animations.effect_of("bulb") == "candle"
        await second.state.container.animations.stop("bulb")
