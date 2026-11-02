from fastapi import APIRouter, Response, status

from app.api.deps import SequencesDep
from app.schemas.sequence import SequenceIn, SequenceOut

router = APIRouter(prefix="/sequences", tags=["sequences"])


@router.get("")
async def list_sequences(sequences: SequencesDep) -> list[SequenceOut]:
    return await sequences.list_all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sequence(body: SequenceIn, sequences: SequencesDep) -> SequenceOut:
    return await sequences.create(body)


@router.get("/{sequence_id}")
async def get_sequence(sequence_id: int, sequences: SequencesDep) -> SequenceOut:
    return await sequences.get(sequence_id)


@router.put("/{sequence_id}")
async def update_sequence(sequence_id: int, body: SequenceIn, sequences: SequencesDep) -> SequenceOut:
    return await sequences.update(sequence_id, body)


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(sequence_id: int, sequences: SequencesDep) -> Response:
    await sequences.delete(sequence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
