from fastapi import APIRouter, Response, status

from app.api.deps import ScenesDep
from app.schemas.device import MessageOut
from app.schemas.scene import SceneApplyOut, SceneIn, SceneOut

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.get("")
async def list_scenes(scenes: ScenesDep) -> list[SceneOut]:
    return await scenes.list_all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scene(body: SceneIn, scenes: ScenesDep) -> SceneOut:
    return await scenes.create(body)


@router.get("/{scene_id}")
async def get_scene(scene_id: int, scenes: ScenesDep) -> SceneOut:
    return await scenes.get(scene_id)


@router.put("/{scene_id}")
async def update_scene(scene_id: int, body: SceneIn, scenes: ScenesDep) -> SceneOut:
    return await scenes.update(scene_id, body)


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(scene_id: int, scenes: ScenesDep) -> Response:
    await scenes.delete(scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{scene_id}/apply", summary="Apply a scene (an animated scene starts looping)")
async def apply_scene(scene_id: int, scenes: ScenesDep) -> SceneApplyOut:
    return SceneApplyOut(results=await scenes.apply(scene_id))


@router.post("/{scene_id}/stop", summary="Stop an animated scene")
async def stop_scene(scene_id: int, scenes: ScenesDep) -> MessageOut:
    stopped = await scenes.stop(scene_id)
    return MessageOut(info="Animation stopped" if stopped else "No animation was running")
