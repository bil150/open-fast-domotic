from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import Json
from app.models import ButtonMapping


class ButtonMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, device_id: str | None = None) -> list[ButtonMapping]:
        query = select(ButtonMapping).order_by(ButtonMapping.id)
        if device_id:
            query = query.where(ButtonMapping.device_id == device_id)
        return list(await self.session.scalars(query))

    async def find(self, device_id: str, event: str) -> ButtonMapping | None:
        return await self.session.scalar(
            select(ButtonMapping).where(ButtonMapping.device_id == device_id, ButtonMapping.event == event)
        )

    async def get(self, mapping_id: int) -> ButtonMapping | None:
        return await self.session.get(ButtonMapping, mapping_id)

    async def upsert(self, device_id: str, event: str, action: Json) -> ButtonMapping:
        mapping = await self.find(device_id, event)
        if mapping:
            mapping.action = action
        else:
            mapping = ButtonMapping(device_id=device_id, event=event, action=action)
            self.session.add(mapping)
        await self.session.flush()
        return mapping

    async def delete(self, mapping: ButtonMapping) -> None:
        await self.session.delete(mapping)
