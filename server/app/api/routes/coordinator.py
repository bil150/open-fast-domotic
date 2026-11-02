from fastapi import APIRouter, Query

from app.api.deps import HubDep
from app.schemas.device import CoordinatorOut, MessageOut

router = APIRouter(prefix="/coordinator", tags=["coordinator"])


@router.get("", summary="Radio status and pairing countdown")
async def coordinator_info(hub: HubDep) -> CoordinatorOut:
    return CoordinatorOut(coordinators=hub.info()["coordinators"])


@router.post(
    "/discovery",
    summary="Allow new devices to pair",
    description="Start the pairing mode of the device while this is active; it is paired automatically.",
)
async def start_discovery(hub: HubDep, seconds: int = Query(30, ge=1, le=254)) -> MessageOut:
    await hub.permit_join(seconds)
    return MessageOut(info=f"Pairing allowed for {seconds} seconds")
