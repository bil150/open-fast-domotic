from fastapi import APIRouter

from app.api.deps import HubDep
from app.schemas.lights import LightsIn, LightsOut
from app.services.light_control import control

router = APIRouter(prefix="/lights", tags=["lights"])


@router.patch("", summary="Switch every light and socket of the home on or off, brighter or dimmer")
async def control_all(body: LightsIn, hub: HubDep) -> LightsOut:
    return LightsOut(results=await control(hub, await hub.list_devices(), body))
