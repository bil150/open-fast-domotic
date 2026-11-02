import logging

from app.core.errors import DeviceNotFoundError, NotFoundError
from app.db.session import SessionFactory
from app.protocols.base import DeviceEvent, LightCommand
from app.repositories import ButtonMappingRepository
from app.schemas.button import ButtonMappingIn, ButtonMappingOut

from .hub import Hub
from .scenes import SceneService

logger = logging.getLogger(__name__)


class ButtonService:
    """Maps button events to actions (scene, toggle, power) and runs them."""

    def __init__(self, sessions: SessionFactory, hub: Hub, scenes: SceneService) -> None:
        self._sessions = sessions
        self._hub = hub
        self._scenes = scenes
        hub.add_event_handler(self.on_event)

    async def list_all(self, device_id: str | None = None) -> list[ButtonMappingOut]:
        async with self._sessions() as session:
            rows = await ButtonMappingRepository(session).list_all(device_id)
            return [ButtonMappingOut.model_validate(r) for r in rows]

    async def set(self, data: ButtonMappingIn) -> ButtonMappingOut:
        await self._hub.get_device(data.device_id)  # raises DeviceNotFoundError
        async with self._sessions() as session:
            mapping = await ButtonMappingRepository(session).upsert(
                data.device_id, data.event, data.action.model_dump()
            )
            await session.commit()
            return ButtonMappingOut.model_validate(mapping)

    async def delete(self, mapping_id: int) -> None:
        async with self._sessions() as session:
            repository = ButtonMappingRepository(session)
            mapping = await repository.get(mapping_id)
            if mapping is None:
                raise NotFoundError(f"Unknown button mapping {mapping_id}")
            await repository.delete(mapping)
            await session.commit()

    async def on_event(self, event: DeviceEvent) -> None:
        if event.kind != "button":
            return
        async with self._sessions() as session:
            mapping = await ButtonMappingRepository(session).find(event.device_id, event.data.get("event", ""))
        if mapping is None:
            return
        action = mapping.action
        logger.info("Button %s %s -> %s", event.device_id, mapping.event, action)
        try:
            if action["type"] == "scene":
                await self._scenes.apply(action["scene_id"])
            elif action["type"] == "toggle":
                await self._hub.toggle(action["device_id"], source="button")
            elif action["type"] == "power":
                await self._hub.set_light(action["device_id"], LightCommand(power=action["state"]), source="button")
        except (DeviceNotFoundError, NotFoundError) as e:
            logger.warning("Button action skipped: %s", e)
        except Exception:
            logger.exception("Button action failed: %s", action)
