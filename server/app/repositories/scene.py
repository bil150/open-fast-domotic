from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import Json
from app.models import Scene


class SceneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Scene]:
        return list(await self.session.scalars(select(Scene).order_by(Scene.name)))

    async def get(self, scene_id: int) -> Scene | None:
        return await self.session.get(Scene, scene_id)

    async def add(self, name: str, actions: list[Json], **columns: Any) -> Scene:
        scene = Scene(name=name, actions=actions, **columns)
        self.session.add(scene)
        await self.session.flush()
        return scene

    async def delete(self, scene: Scene) -> None:
        await self.session.delete(scene)
