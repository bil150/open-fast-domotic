from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_groups, get_rooms
from app.schemas.lights import LightsIn, LightsOut
from app.schemas.zone import ZoneIn, ZoneOut
from app.services.zones import ZoneService


def _zone_router(prefix: str, label: str, get_service: Callable[..., ZoneService[Any]]) -> APIRouter:
    """Rooms and groups expose the same CRUD, only the service behind it differs."""
    router = APIRouter(prefix=prefix, tags=[prefix.strip("/")])
    ServiceDep = Annotated[ZoneService[Any], Depends(get_service)]

    @router.get("", summary=f"List the {label}s")
    async def list_zones(service: ServiceDep) -> list[ZoneOut]:
        return await service.list_all()

    @router.post("", status_code=status.HTTP_201_CREATED, summary=f"Create a {label}")
    async def create_zone(body: ZoneIn, service: ServiceDep) -> ZoneOut:
        return await service.create(body)

    @router.get("/{zone_id}", summary=f"Get a {label}")
    async def get_zone(zone_id: int, service: ServiceDep) -> ZoneOut:
        return await service.get(zone_id)

    @router.put("/{zone_id}", summary=f"Rename a {label} or change its lights")
    async def update_zone(zone_id: int, body: ZoneIn, service: ServiceDep) -> ZoneOut:
        return await service.update(zone_id, body)

    @router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete a {label}")
    async def delete_zone(zone_id: int, service: ServiceDep) -> Response:
        await service.delete(zone_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.patch("/{zone_id}/light", summary=f"Switch the lights of a {label} on or off, brighter or dimmer")
    async def control_zone(zone_id: int, body: LightsIn, service: ServiceDep) -> LightsOut:
        return LightsOut(results=await service.control(zone_id, body))

    return router


rooms_router = _zone_router("/rooms", "room", get_rooms)
groups_router = _zone_router("/groups", "group", get_groups)
