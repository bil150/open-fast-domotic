from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone


class ZoneRepository[T: Zone]:
    """Rooms and groups are stored the same way: a name and a list of device ids."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def list_all(self) -> list[T]:
        return list(await self.session.scalars(select(self.model).order_by(self.model.name)))

    async def get(self, zone_id: int) -> T | None:
        return await self.session.get(self.model, zone_id)

    async def add(self, name: str, device_ids: list[str]) -> T:
        zone = self.model(name=name, device_ids=device_ids)
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def delete(self, zone: T) -> None:
        await self.session.delete(zone)
