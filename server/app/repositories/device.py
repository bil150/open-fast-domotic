from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import Json
from app.models import Animation, DeviceMeta, DeviceName


class DeviceNameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> dict[str, str]:
        rows = await self.session.scalars(select(DeviceName))
        return {row.device_id: row.name for row in rows}

    async def set(self, device_id: str, name: str) -> None:
        await self.session.merge(DeviceName(device_id=device_id, name=name))

    async def delete(self, device_id: str) -> None:
        await self.session.execute(delete(DeviceName).where(DeviceName.device_id == device_id))


class DeviceMetaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> dict[str, Json]:
        rows = await self.session.scalars(select(DeviceMeta))
        return {row.device_id: row.data for row in rows}

    async def set(self, device_id: str, data: Json) -> None:
        await self.session.merge(DeviceMeta(device_id=device_id, data=data))

    async def delete(self, device_id: str) -> None:
        await self.session.execute(delete(DeviceMeta).where(DeviceMeta.device_id == device_id))


class AnimationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> dict[str, list[Json]]:
        rows = await self.session.scalars(select(Animation))
        return {row.device_id: row.keys for row in rows}

    async def set(self, device_id: str, keys: list[Json]) -> None:
        await self.session.merge(Animation(device_id=device_id, keys=keys))

    async def delete(self, device_id: str) -> None:
        await self.session.execute(delete(Animation).where(Animation.device_id == device_id))
