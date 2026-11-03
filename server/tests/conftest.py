import copy
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

from app.core.config import Settings
from app.main import create_app
from app.protocols.base import BaseCoordinator, DeviceEvent, LightCommand


def make_device(device_id: str, name: str, type_: str, capabilities: list[str], **state) -> dict:
    return {
        "id": device_id,
        "protocol": "fake",
        "name": name,
        "model": name,
        "manufacturer": "ACME",
        "type": type_,
        "capabilities": capabilities,
        "online": None,
        "nwk": "0x0001",
        "last_seen": None,
        "lqi": 200,
        "rssi": -50,
        "state": state,
    }


class FakeCoordinator(BaseCoordinator):
    """In-memory protocol: records the commands, can simulate unreachable devices."""

    protocol = "fake"

    def __init__(self) -> None:
        super().__init__()
        self.devices = {
            "bulb": make_device("bulb", "Color bulb", "BULB", ["on_off", "brightness", "color", "color_temp"]),
            "white": make_device("white", "White bulb", "BULB", ["on_off", "brightness", "color_temp"]),
            "socket": make_device("socket", "Socket", "POWER_SOCKET", ["on_off"]),
            "sensor": make_device(
                "sensor", "Sensor", "TEMPERATURE_SENSOR", ["temperature", "battery"], temperature=21.5
            ),
            "button": make_device("button", "Remote", "BUTTON", ["button", "battery"]),
        }
        self.commands: list[tuple[str, str, object]] = []
        self.unreachable: set[str] = set()
        self.started = False
        self.permit_seconds: int | None = None
        self.removed: list[str] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    async def list_devices(self) -> list[dict]:
        return [copy.deepcopy(d) for d in self.devices.values()]

    async def get_device(self, device_id: str) -> dict | None:
        device = self.devices.get(device_id)
        return copy.deepcopy(device) if device else None

    def owns(self, device_id: str) -> bool:
        return device_id in self.devices

    async def remove_device(self, device_id: str) -> None:
        self.removed.append(device_id)
        self.devices.pop(device_id, None)

    async def permit_join(self, seconds: int) -> None:
        self.permit_seconds = seconds

    async def set_light(self, device_id: str, command: LightCommand) -> bool:
        self.commands.append((device_id, "light", command))
        if device_id in self.unreachable:
            self.devices[device_id]["online"] = False
            return False
        state = self.devices[device_id]["state"]
        if command.power is not None:
            state["power"] = command.power
        if command.brightness is not None:
            state["brightness"] = command.brightness
        self.devices[device_id]["online"] = True
        return True

    async def toggle(self, device_id: str) -> bool:
        self.commands.append((device_id, "toggle", None))
        return device_id not in self.unreachable

    async def refresh(self, device_id: str) -> dict | None:
        self.commands.append((device_id, "refresh", None))
        return await self.get_device(device_id)

    def info(self) -> dict:
        return {"protocol": self.protocol, "ready": True}

    def lights(self, device_id: str) -> list[LightCommand]:
        return [c for d, kind, c in self.commands if d == device_id and kind == "light"]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=str(tmp_path), enable_z=False, restore_animations=False, _env_file=None)


@pytest.fixture
def fake() -> FakeCoordinator:
    return FakeCoordinator()


@pytest_asyncio.fixture
async def app(settings, fake):
    application = create_app(settings, [fake])
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http


@pytest.fixture
def container(app):
    return app.state.container


def button_event(device_id: str, event: str) -> DeviceEvent:
    return DeviceEvent(device_id, "button", {"event": event, "args": "[]", "at": "2026-01-01T00:00:00"})


def fake_cluster(cluster_id: int, name: str = "cluster", ep_attribute: str = "cluster", **attrs):
    """Stand-in for a zigpy cluster. `commands` records what was sent."""
    cluster = SimpleNamespace(
        cluster_id=cluster_id,
        name=name,
        ep_attribute=ep_attribute,
        commands=[],
        options=[],
        fail=None,
        cache=dict(attrs),
        listeners=[],
        server_commands={},
        client_commands={},
    )

    async def command(command_id, *args, **options):
        if cluster.fail:
            raise cluster.fail
        cluster.commands.append((command_id, args))
        cluster.options.append(options)

    cluster.command = command
    cluster.get = lambda attribute, default=None: cluster.cache.get(attribute, default)
    cluster.add_listener = cluster.listeners.append
    cluster.find_attribute = lambda attrid: SimpleNamespace(name=attrid) if isinstance(attrid, str) else None
    return cluster


def fake_zigpy_device(ieee: str, in_clusters=(), out_clusters=(), nwk: int = 0x1234):
    endpoint = SimpleNamespace(
        in_clusters={c.cluster_id: c for c in in_clusters},
        out_clusters={c.cluster_id: c for c in out_clusters},
        profile_id=260,
        device_type=0,
    )
    return SimpleNamespace(
        ieee=ieee,
        nwk=nwk,
        endpoints={0: SimpleNamespace(in_clusters={}, out_clusters={}), 1: endpoint},
        model="M",
        manufacturer="ACME",
        last_seen=None,
        lqi=100,
        rssi=-60,
    )
