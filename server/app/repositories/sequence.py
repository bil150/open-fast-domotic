from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sequence


class SequenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Sequence]:
        return list(await self.session.scalars(select(Sequence).order_by(Sequence.id)))

    async def get(self, sequence_id: int) -> Sequence | None:
        return await self.session.get(Sequence, sequence_id)

    async def add(self, **fields: Any) -> Sequence:
        sequence = Sequence(**fields)
        self.session.add(sequence)
        await self.session.flush()
        return sequence

    async def delete(self, sequence: Sequence) -> None:
        await self.session.delete(sequence)
