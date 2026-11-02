import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.protocols.base import DeviceEvent
from tests.conftest import FakeCoordinator, button_event


@pytest.fixture
def sync_client(settings):
    fake = FakeCoordinator()
    with TestClient(create_app(settings, [fake])) as client:
        yield client, fake


def test_websocket_pushes_state_and_button_events(sync_client):
    client, fake = sync_client
    with client.websocket_connect("/api/v1/ws") as websocket:
        client.portal.call(
            lambda: fake.emit(DeviceEvent("sensor", "state", {"state": {"temperature": 22.0}, "online": True}))
        )
        assert websocket.receive_json() == {
            "type": "state",
            "device_id": "sensor",
            "data": {"state": {"temperature": 22.0}, "online": True},
        }
        client.portal.call(lambda: fake.emit(button_event("button", "on_off.on")))
        message = websocket.receive_json()
        assert message["type"] == "button" and message["data"]["event"] == "on_off.on"


def test_websocket_unsubscribes_on_disconnect(sync_client):
    client, _ = sync_client
    hub = client.app.state.container.hub
    with client.websocket_connect("/api/v1/ws") as websocket:
        websocket.send_text("ping")  # keep-alive is accepted
        assert len(hub._ws_queues) == 1
    for _ in range(50):
        if not hub._ws_queues:
            break
        client.portal.call(lambda: None)
    assert not hub._ws_queues


def test_lifespan_starts_and_stops_coordinators(sync_client):
    client, fake = sync_client
    assert fake.started
    assert client.get("/api/v1").json()["name"] == "open-fast-domotic"


def test_stream_applies_color_and_brightness_without_a_response(sync_client):
    client, fake = sync_client
    with client.websocket_connect("/api/v1/stream") as websocket:
        websocket.send_json({"device_id": "nobody", "brightness": 10})  # unknown: ignored
        websocket.send_json({"device_id": "bulb", "brightness": "bright"})  # invalid: ignored
        websocket.send_json({"device_id": "bulb", "hex_color": "red"})  # invalid: ignored
        websocket.send_json(["not", "an", "object"])  # ignored too, and the connection stays
        websocket.send_json({"device_id": "bulb", "brightness": 200, "hex_color": "#ff0000"})
        for _ in range(200):
            if fake.lights("bulb"):
                break
            client.portal.call(lambda: None)
    assert [(c.brightness, c.hex_color) for c in fake.lights("bulb")] == [(200, "#ff0000")]
