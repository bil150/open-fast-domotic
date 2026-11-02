from fastapi import APIRouter, Response, status

from app.api.deps import ButtonsDep
from app.schemas.button import ButtonMappingIn, ButtonMappingOut

router = APIRouter(prefix="/buttons", tags=["buttons"])


@router.get("")
async def list_mappings(buttons: ButtonsDep, device_id: str | None = None) -> list[ButtonMappingOut]:
    return await buttons.list_all(device_id)


@router.put(
    "",
    summary="Set what a button event triggers",
    description="One action per (device_id, event). The events a button emitted are in its state.last_button.",
)
async def set_mapping(body: ButtonMappingIn, buttons: ButtonsDep) -> ButtonMappingOut:
    return await buttons.set(body)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: int, buttons: ButtonsDep) -> Response:
    await buttons.delete(mapping_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
