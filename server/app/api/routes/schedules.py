from fastapi import APIRouter, Response, status

from app.api.deps import SchedulesDep
from app.schemas.schedule import ScheduleIn, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(schedules: SchedulesDep) -> list[ScheduleOut]:
    return await schedules.list_all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleIn, schedules: SchedulesDep) -> ScheduleOut:
    return await schedules.create(body)


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int, schedules: SchedulesDep) -> ScheduleOut:
    return await schedules.get(schedule_id)


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, body: ScheduleIn, schedules: SchedulesDep) -> ScheduleOut:
    return await schedules.update(schedule_id, body)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, schedules: SchedulesDep) -> Response:
    await schedules.delete(schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
