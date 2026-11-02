from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, DeviceNotFoundError, NotFoundError
from app.db.session import SessionFactory
from app.models.zone import Group, Room, Zone
from app.repositories.zone import ZoneRepository
from app.schemas.lights import LightsIn
from app.schemas.zone import ZoneIn, ZoneOut

from .hub import Hub
from .light_control import control


class ZoneService[T: Zone]:
    """CRUD of rooms or groups: named sets of devices that scenes and effects can target."""

    def __init__(self, sessions: SessionFactory, hub: Hub, model: type[T], label: str) -> None:
        self._sessions = sessions
        self._hub = hub
        self._model = model
        self._label = label

    async def _free_devices(self, repository: ZoneRepository[T], keep: int | None, device_ids: list[str]) -> None:
        """Hook: a room takes its devices away from the other rooms."""

    async def list_all(self) -> list[ZoneOut]:
        async with self._sessions() as session:
            return [ZoneOut.model_validate(z) for z in await ZoneRepository(session, self._model).list_all()]

    async def get(self, zone_id: int) -> ZoneOut:
        return ZoneOut.model_validate(await self.resolve(zone_id))

    async def resolve(self, zone_id: int) -> T:
        async with self._sessions() as session:
            zone = await ZoneRepository(session, self._model).get(zone_id)
        if zone is None:
            raise NotFoundError(f"Unknown {self._label} {zone_id}")
        return zone

    async def device_ids(self, zone_id: int) -> list[str]:
        return list((await self.resolve(zone_id)).device_ids)

    async def control(self, zone_id: int, order: LightsIn) -> dict[str, bool]:
        """Switch every light and socket of the zone, or make them brighter or dimmer."""
        devices = []
        for device_id in await self.device_ids(zone_id):
            try:
                devices.append(await self._hub.get_device(device_id))
            except DeviceNotFoundError:
                continue  # a device removed from the network
        return await control(self._hub, devices, order)

    async def create(self, data: ZoneIn) -> ZoneOut:
        try:
            async with self._sessions() as session:
                repository = ZoneRepository(session, self._model)
                await self._free_devices(repository, None, data.device_ids)
                zone = await repository.add(data.name, data.device_ids)
                await session.commit()
                return ZoneOut.model_validate(zone)
        except IntegrityError:
            raise ConflictError(f"A {self._label} named '{data.name}' already exists") from None

    async def update(self, zone_id: int, data: ZoneIn) -> ZoneOut:
        try:
            async with self._sessions() as session:
                repository = ZoneRepository(session, self._model)
                zone = await repository.get(zone_id)
                if zone is None:
                    raise NotFoundError(f"Unknown {self._label} {zone_id}")
                await self._free_devices(repository, zone_id, data.device_ids)
                zone.name = data.name
                zone.device_ids = data.device_ids
                await session.commit()
                return ZoneOut.model_validate(zone)
        except IntegrityError:
            raise ConflictError(f"A {self._label} named '{data.name}' already exists") from None

    async def delete(self, zone_id: int) -> None:
        async with self._sessions() as session:
            repository = ZoneRepository(session, self._model)
            zone = await repository.get(zone_id)
            if zone is None:
                raise NotFoundError(f"Unknown {self._label} {zone_id}")
            await repository.delete(zone)
            await session.commit()


class RoomService(ZoneService[Room]):
    def __init__(self, sessions: SessionFactory, hub: Hub) -> None:
        super().__init__(sessions, hub, Room, "room")

    async def _free_devices(self, repository: ZoneRepository[Room], keep: int | None, device_ids: list[str]) -> None:
        taken = set(device_ids)
        for other in await repository.list_all():
            if other.id != keep and taken & set(other.device_ids):
                other.device_ids = [d for d in other.device_ids if d not in taken]


class GroupService(ZoneService[Group]):
    def __init__(self, sessions: SessionFactory, hub: Hub) -> None:
        super().__init__(sessions, hub, Group, "group")
