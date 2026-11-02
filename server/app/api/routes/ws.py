import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.errors import DeviceNotFoundError
from app.schemas.lights import StreamIn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["live"])


@router.websocket("/ws")
async def live_updates(websocket: WebSocket) -> None:
    """Pushes {type, device_id, data} for every device change:
    type is "state", "button", "joined" or "left"."""
    hub = websocket.app.state.container.hub
    await websocket.accept()
    queue = hub.subscribe_ws()
    incoming = asyncio.ensure_future(websocket.receive_text())  # also detects the disconnection
    try:
        while True:
            outgoing = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({incoming, outgoing}, return_when=asyncio.FIRST_COMPLETED)
            if incoming in done:
                outgoing.cancel()
                try:
                    incoming.result()  # a client message is just a keep-alive
                except WebSocketDisconnect:
                    return
                incoming = asyncio.ensure_future(websocket.receive_text())
            else:
                await websocket.send_json(outgoing.result())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        incoming.cancel()
        hub.unsubscribe_ws(queue)


@router.websocket("/stream")
async def stream_light(websocket: WebSocket) -> None:
    """Live color and brightness for effects such as the music mode. The client sends
    {"device_id": "...", "brightness": 0..255, "hex_color": "#rrggbb"} (the last two are optional)
    as fast as it likes: the server keeps only the newest values per device while the radio is busy,
    and does not wait for the bulbs to answer."""
    hub = websocket.app.state.container.hub
    await websocket.accept()
    latest: dict[str, dict[str, Any]] = {}
    wake = asyncio.Event()

    async def send_one(device_id: str, values: dict[str, Any]) -> None:
        try:
            await hub.stream_light(device_id, **values)
        except DeviceNotFoundError:
            pass
        except Exception:
            logger.exception("Streamed light failed for %s", device_id)

    async def pump() -> None:
        while True:
            await wake.wait()
            wake.clear()
            batch = dict(latest)
            latest.clear()
            await asyncio.gather(*(send_one(d, v) for d, v in batch.items()))

    pumping = asyncio.ensure_future(pump())
    try:
        while True:
            try:
                message = StreamIn.model_validate_json(await websocket.receive_text())
            except ValidationError:
                continue  # not a valid message: ignored, the connection stays
            values = message.model_dump(exclude={"device_id"}, exclude_none=True)
            if values:
                latest[message.device_id] = {**latest.get(message.device_id, {}), **values}  # keep a color not yet sent
                wake.set()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        pumping.cancel()
