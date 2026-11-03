from sqlalchemy import delete, select

from app.core.types import Json
from app.db.session import SessionFactory
from app.models import ButtonMapping, Scene
from app.models.zone import Group, Room
from app.repositories import DeviceNameRepository

from .animations import AnimationService
from .device_meta import DeviceMetaService
from .hub import Hub


class DeviceCleanup:
    """Forgets a removed device everywhere the server kept something about it: its name, what was probed,
    its animation, the buttons it triggers, its place in rooms and groups, its part in scenes."""

    def __init__(
        self, sessions: SessionFactory, hub: Hub, meta: DeviceMetaService, animations: AnimationService
    ) -> None:
        self._sessions = sessions
        self._meta = meta
        self._animations = animations
        hub.add_removal_handler(self.forget)

    async def forget(self, device_id: str) -> None:
        await self._animations.stop(device_id)  # also deletes the saved animation
        await self._meta.forget(device_id)
        async with self._sessions() as session:
            await DeviceNameRepository(session).delete(device_id)
            await session.execute(delete(ButtonMapping).where(ButtonMapping.device_id == device_id))
            for mapping in await session.scalars(select(ButtonMapping)):
                if mapping.action.get("device_id") == device_id:  # a button that drove this device
                    await session.delete(mapping)
            for model in (Room, Group):
                for zone in await session.scalars(select(model)):
                    if device_id in zone.device_ids:
                        zone.device_ids = [d for d in zone.device_ids if d != device_id]
            for scene in await session.scalars(select(Scene)):
                self._clean_scene(scene, device_id)
            await session.commit()

    @staticmethod
    def _clean_scene(scene: Scene, device_id: str) -> None:
        # JSON columns are only saved when they are replaced, not when they are changed in place
        if scene.assignments and device_id in scene.assignments:
            scene.assignments = {d: i for d, i in scene.assignments.items() if d != device_id}
        if scene.switches and device_id in scene.switches:
            scene.switches = {d: on for d, on in scene.switches.items() if d != device_id}
        if any(a.get("device_id") == device_id for a in scene.actions):
            actions: list[Json] = [a for a in scene.actions if a.get("device_id") != device_id]
            scene.actions = actions
