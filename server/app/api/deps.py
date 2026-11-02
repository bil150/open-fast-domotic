from typing import Annotated

from fastapi import Depends, Request

from app.core.container import Container
from app.services.animations import AnimationService
from app.services.buttons import ButtonService
from app.services.hub import Hub
from app.services.scenes import SceneService
from app.services.schedules import ScheduleService
from app.services.sequences import SequenceService
from app.services.zones import GroupService, RoomService


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_hub(container: ContainerDep) -> Hub:
    return container.hub


def get_animations(container: ContainerDep) -> AnimationService:
    return container.animations


def get_scenes(container: ContainerDep) -> SceneService:
    return container.scenes


def get_rooms(container: ContainerDep) -> RoomService:
    return container.rooms


def get_groups(container: ContainerDep) -> GroupService:
    return container.groups


def get_schedules(container: ContainerDep) -> ScheduleService:
    return container.schedules


def get_sequences(container: ContainerDep) -> SequenceService:
    return container.sequences


def get_buttons(container: ContainerDep) -> ButtonService:
    return container.buttons


HubDep = Annotated[Hub, Depends(get_hub)]
AnimationsDep = Annotated[AnimationService, Depends(get_animations)]
ScenesDep = Annotated[SceneService, Depends(get_scenes)]
SchedulesDep = Annotated[ScheduleService, Depends(get_schedules)]
SequencesDep = Annotated[SequenceService, Depends(get_sequences)]
ButtonsDep = Annotated[ButtonService, Depends(get_buttons)]
