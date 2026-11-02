from fastapi import APIRouter

from app.api.deps import AnimationsDep, HubDep
from app.core.errors import DeviceUnreachableError, UnsupportedCommandError
from app.schemas.animation import AnimationIn, EffectIn, EffectOut
from app.schemas.device import DeviceOut, DeviceRename, DevicesOut, MessageOut
from app.schemas.light import LightRequest

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def list_devices(hub: HubDep) -> DevicesOut:
    return DevicesOut(devices=await hub.list_devices())


@router.get("/{device_id}", summary="Device with its endpoints and clusters")
async def get_device(device_id: str, hub: HubDep) -> DeviceOut:
    return await hub.get_device(device_id)


@router.patch("/{device_id}")
async def rename_device(device_id: str, body: DeviceRename, hub: HubDep) -> DeviceOut:
    return await hub.rename_device(device_id, body.name)


@router.patch("/{device_id}/light", summary="Power, brightness, color or white")
async def set_light(device_id: str, body: LightRequest, hub: HubDep) -> DeviceOut:
    command = body.to_command()
    await hub.check_light_command(device_id, command)
    if not await hub.set_light(device_id, command):
        raise DeviceUnreachableError("The device did not answer")
    return await hub.get_device(device_id)


@router.post("/{device_id}/toggle")
async def toggle(device_id: str, hub: HubDep) -> DeviceOut:
    if not await hub.toggle(device_id):
        raise DeviceUnreachableError("The device did not answer")
    return await hub.get_device(device_id)


@router.post(
    "/{device_id}/refresh",
    summary="Read the current values (temperature, battery, light state)",
    description="Sleeping sensors and buttons only answer while awake: press the device's button just before calling.",
)
async def refresh(device_id: str, hub: HubDep) -> DeviceOut:
    return await hub.refresh_device(device_id)


@router.put("/{device_id}/animation")
async def start_animation(device_id: str, body: AnimationIn, animations: AnimationsDep) -> MessageOut:
    await animations.start(device_id, body.keys)
    return MessageOut(info="Animation started")


@router.get("/{device_id}/effect", summary="The FX running on a bulb, if any")
async def get_effect(device_id: str, hub: HubDep, animations: AnimationsDep) -> EffectOut:
    await hub.get_device(device_id)  # raises DeviceNotFoundError
    return EffectOut(effect=animations.effect_of(device_id))


@router.put("/{device_id}/effect", summary="Start a FX (fire, candle) on a bulb; any manual command stops it")
async def start_effect(device_id: str, body: EffectIn, hub: HubDep, animations: AnimationsDep) -> EffectOut:
    device = await hub.get_device(device_id)
    if "brightness" not in device.capabilities:
        raise UnsupportedCommandError("FX is for bulbs only")
    await animations.start_effect(device_id, body.effect, body.brightness)
    return EffectOut(effect=body.effect)


@router.delete("/{device_id}/animation")
async def stop_animation(device_id: str, animations: AnimationsDep) -> MessageOut:
    stopped = await animations.stop(device_id)
    return MessageOut(info="Animation stopped" if stopped else "No animation was running")
