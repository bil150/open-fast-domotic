from fastapi import APIRouter

from app.api.routes import buttons, coordinator, devices, lights, scenes, schedules, sequences, ws, zones

api_router = APIRouter()
for module in (coordinator, devices, lights, scenes, schedules, sequences, buttons, ws):
    api_router.include_router(module.router)
api_router.include_router(zones.rooms_router)
api_router.include_router(zones.groups_router)
