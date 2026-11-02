import pytest_asyncio

from app.db.session import create_engine, create_session_factory, init_db
from app.repositories import (
    AnimationRepository,
    ButtonMappingRepository,
    DeviceMetaRepository,
    DeviceNameRepository,
    SceneRepository,
    ScheduleRepository,
)


@pytest_asyncio.fixture
async def session(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_db(engine)
    async with create_session_factory(engine)() as session:
        yield session
    await engine.dispose()


async def test_device_names(session):
    names = DeviceNameRepository(session)
    await names.set("a", "Kitchen")
    await names.set("a", "Hall")  # replaces
    await names.set("b", "Garage")
    assert await names.get_all() == {"a": "Hall", "b": "Garage"}
    await names.delete("a")
    assert await names.get_all() == {"b": "Garage"}


async def test_device_meta_and_animations_roundtrip_json(session):
    meta = DeviceMetaRepository(session)
    await meta.set("a", {"color_capabilities": 31, "mireds_min": 153})
    assert (await meta.get_all())["a"]["mireds_min"] == 153

    animations = AnimationRepository(session)
    await animations.set("a", [{"hue": 1}])
    await animations.set("a", [{"hue": 2}])
    assert await animations.get_all() == {"a": [{"hue": 2}]}
    await animations.delete("a")
    assert await animations.get_all() == {}


async def test_scenes_and_cascade_to_schedules(session):
    scenes, schedules = SceneRepository(session), ScheduleRepository(session)
    scene = await scenes.add("Night", [{"device_id": "a", "power": False}])
    await schedules.add(name="s", cron="0 22 * * *", scene_id=scene.id)
    assert [s.name for s in await scenes.list_all()] == ["Night"]
    assert len(await schedules.list_all()) == 1

    await scenes.delete(scene)
    await session.commit()
    session.expunge_all()
    assert await schedules.list_all() == []


async def test_button_mapping_is_unique_per_device_and_event(session):
    buttons = ButtonMappingRepository(session)
    first = await buttons.upsert("b", "on_off.on", {"type": "toggle", "device_id": "x"})
    second = await buttons.upsert("b", "on_off.on", {"type": "power", "device_id": "x", "state": True})
    await buttons.upsert("b", "on_off.off", {"type": "toggle", "device_id": "x"})
    assert first.id == second.id
    assert len(await buttons.list_all()) == 2
    assert len(await buttons.list_all("b")) == 2
    assert (await buttons.find("b", "on_off.on")).action["type"] == "power"
    assert await buttons.find("b", "nope") is None
