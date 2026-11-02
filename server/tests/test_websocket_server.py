"""The WebSocket must work behind a real uvicorn, not only with Starlette's test client:
without a WebSocket library installed (uvicorn[standard]), uvicorn answers 404 to the upgrade."""

import asyncio
import json
import socket

import pytest
import uvicorn
import websockets

from app.main import create_app
from app.protocols.base import DeviceEvent
from tests.conftest import FakeCoordinator


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


@pytest.fixture
async def live_server(settings):
    fake = FakeCoordinator()
    config = uvicorn.Config(create_app(settings, [fake]), host="127.0.0.1", port=free_port(), log_level="warning")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        if task.done():
            task.result()  # the server crashed: raise its error instead of waiting forever
        await asyncio.sleep(0.05)
    yield fake, config.port
    server.should_exit = True
    await task


async def test_real_server_accepts_the_websocket_and_pushes_events(live_server):
    fake, port = live_server
    async with websockets.connect(f"ws://127.0.0.1:{port}/api/v1/ws") as websocket:
        fake.emit(DeviceEvent("sensor", "state", {"state": {"temperature": 21.5}, "online": True}))
        message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
    assert message == {
        "type": "state",
        "device_id": "sensor",
        "data": {"state": {"temperature": 21.5}, "online": True},
    }
