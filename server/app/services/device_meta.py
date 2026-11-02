from app.core.types import Json
from app.db.session import SessionFactory
from app.repositories import DeviceMetaRepository


class DeviceMetaService:
    """What was probed from the devices. Read synchronously from a cache (it is
    needed on every command), written through to the database."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions
        self._cache: dict[str, Json] = {}

    async def load(self) -> None:
        async with self._sessions() as session:
            self._cache = await DeviceMetaRepository(session).get_all()

    def get(self, device_id: str) -> Json:
        return self._cache.get(device_id, {})

    async def save(self, device_id: str, data: Json) -> None:
        self._cache[device_id] = data
        async with self._sessions() as session:
            await DeviceMetaRepository(session).set(device_id, data)
            await session.commit()
