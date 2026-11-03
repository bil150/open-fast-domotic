"""Composition root: builds the services and wires them together."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.session import SessionFactory, create_engine, create_session_factory, init_db
from app.protocols.base import BaseCoordinator
from app.services.animations import AnimationService
from app.services.buttons import ButtonService
from app.services.device_cleanup import DeviceCleanup
from app.services.device_meta import DeviceMetaService
from app.services.hub import Hub
from app.services.scenes import SceneService
from app.services.scheduler import Scheduler
from app.services.schedules import ScheduleService
from app.services.sequences import SequenceService
from app.services.zones import GroupService, RoomService


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    sessions: SessionFactory
    meta: DeviceMetaService
    hub: Hub
    animations: AnimationService
    scenes: SceneService
    buttons: ButtonService
    schedules: ScheduleService
    scheduler: Scheduler
    sequences: SequenceService
    rooms: RoomService
    groups: GroupService

    async def start(self) -> None:
        await init_db(self.engine)
        await self.meta.load()
        await self.hub.start()
        if self.settings.restore_animations:
            await self.animations.restore()
            await self.scenes.restore()
            await self.sequences.restore()
        self.scheduler.start()

    async def stop(self) -> None:
        await self.scheduler.stop()
        await self.sequences.shutdown()
        await self.scenes.shutdown()
        await self.animations.shutdown()
        await self.hub.stop()
        await self.engine.dispose()


def build_container(settings: Settings, coordinators: list[BaseCoordinator] | None = None) -> Container:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    meta = DeviceMetaService(sessions)

    hub = Hub(sessions)
    if coordinators is None:
        coordinators = []
        if settings.enable_z:
            from app.protocols.z.coordinator import ZCoordinator

            coordinators.append(ZCoordinator(settings, meta))
    for coordinator in coordinators:
        hub.register(coordinator)

    animations = AnimationService(sessions, hub)
    DeviceCleanup(sessions, hub, meta, animations)  # registers itself with the hub
    rooms = RoomService(sessions, hub)
    groups = GroupService(sessions, hub)
    scenes = SceneService(sessions, hub, rooms, groups)
    buttons = ButtonService(sessions, hub, scenes)
    schedules = ScheduleService(sessions)
    scheduler = Scheduler(schedules, scenes)
    sequences = SequenceService(sessions, scenes)
    return Container(
        settings,
        engine,
        sessions,
        meta,
        hub,
        animations,
        scenes,
        buttons,
        schedules,
        scheduler,
        sequences,
        rooms,
        groups,
    )
