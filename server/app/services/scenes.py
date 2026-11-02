import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, DeviceNotFoundError, NotFoundError
from app.core.speeds import MIN_GLIDE
from app.core.types import Json
from app.db.session import SessionFactory
from app.models import Scene
from app.protocols.base import Capability, LightCommand
from app.repositories import SceneRepository
from app.schemas.scene import SceneAction, SceneIn, SceneOut

from . import color_path
from .hub import Hub
from .zones import GroupService, RoomService

logger = logging.getLogger(__name__)

# Source of the commands of a running animation. Any other source (a person, a button, another
# scene) that reaches one of its lights stops it.
ANIMATION_SOURCE = "scene-animation"
# A lamp that is sent a command while it is still gliding ends the glide at once: the color jumps to its
# target instead of getting there smoothly. So a glide is always shorter than its slot by this many seconds,
# and nothing is sent to the lamp before the slot is over.
GUARD = 0.1
STEP_TIMEOUT = 3.0  # seconds: longest wait for a lamp in one step of an animation
# A request that starts an animated scene is answered within this time, whatever the radio is doing: the first
# step goes on in the background, in the order of the lamps' queues, and stop can end it at any moment.
START_WAIT = 3.0
SLOW_COMMAND = 1.0  # seconds: a command that took longer makes the glides stop and start, worth a warning


class SceneService:
    def __init__(
        self,
        sessions: SessionFactory,
        hub: Hub,
        rooms: RoomService,
        groups: GroupService,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sessions = sessions
        self._hub = hub
        self._rooms = rooms
        self._groups = groups
        self._sleep = sleep
        self._clock = clock
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._lights_of: dict[int, set[str]] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        hub.add_command_guard(self._on_command)

    @staticmethod
    def _dump(actions: list[SceneAction]) -> list[Json]:
        return [a.model_dump(exclude_none=True, exclude_defaults=False) for a in actions]

    @staticmethod
    def _columns(data: SceneIn) -> Json:
        """What is stored besides the name: the same columns whatever the kind of scene."""
        return {
            "actions": SceneService._dump(data.actions),
            "target": data.target.model_dump() if data.target else None,
            "palette": [c.model_dump(exclude_none=True) for c in data.palette] or None,
            "assignments": data.assignments or None,
            "switches": data.switches or None,
            "speed": data.speed if data.target else None,
            "fade": data.fade_seconds,
            "animated": data.animated,
            "duration": data.fade_seconds or 5.0,  # an animated scene: each color lasts as long as the glide
        }

    @staticmethod
    def _timing(scene: SceneOut) -> tuple[float, float]:
        """(seconds each color lasts, seconds of the glide to it). An animation glides for the whole time of
        a color and never for less than MIN_GLIDE, whatever was saved: it does not stop on a color and jump."""
        if scene.animated:
            seconds = max(scene.duration, scene.fade, MIN_GLIDE)
            return seconds, seconds
        return scene.duration, scene.fade

    def _running(self, scene_id: int) -> bool:
        task = self._tasks.get(scene_id)
        return task is not None and not task.done()

    def _out(self, scene: Scene) -> SceneOut:
        out = SceneOut.model_validate(scene)
        out.running = self._running(scene.id)
        return out

    async def _target_devices(self, target: Json) -> list[str]:
        service = self._rooms if target["type"] == "room" else self._groups
        return await service.device_ids(target["id"])

    async def list_all(self) -> list[SceneOut]:
        async with self._sessions() as session:
            return [self._out(s) for s in await SceneRepository(session).list_all()]

    async def get(self, scene_id: int) -> SceneOut:
        async with self._sessions() as session:
            scene = await SceneRepository(session).get(scene_id)
        if scene is None:
            raise NotFoundError(f"Unknown scene {scene_id}")
        return self._out(scene)

    async def create(self, data: SceneIn) -> SceneOut:
        if data.target:
            await self._target_devices(data.target.model_dump())  # the room/group must exist
        try:
            async with self._sessions() as session:
                scene = await SceneRepository(session).add(data.name, **self._columns(data))
                await session.commit()
                return self._out(scene)
        except IntegrityError:
            raise ConflictError(f"A scene named '{data.name}' already exists") from None

    async def update(self, scene_id: int, data: SceneIn) -> SceneOut:
        if data.target:
            await self._target_devices(data.target.model_dump())
        try:
            async with self._sessions() as session:
                scene = await SceneRepository(session).get(scene_id)
                if scene is None:
                    raise NotFoundError(f"Unknown scene {scene_id}")
                was_running = self._running(scene_id)
                scene.name = data.name
                for column, value in self._columns(data).items():
                    setattr(scene, column, value)
                if not data.animated:
                    scene.running = False
                await session.commit()
        except IntegrityError:
            raise ConflictError(f"A scene named '{data.name}' already exists") from None
        await self._cancel(scene_id)  # restart from the first color with the new settings
        if was_running and data.animated:
            await self._start_animation(await self.get(scene_id), persist=False)
        return await self.get(scene_id)

    async def delete(self, scene_id: int) -> None:
        async with self._sessions() as session:
            repository = SceneRepository(session)
            scene = await repository.get(scene_id)
            if scene is None:
                raise NotFoundError(f"Unknown scene {scene_id}")
            await repository.delete(scene)
            await session.commit()
        await self._cancel(scene_id)
        self._locks.pop(scene_id, None)

    # --- what a light must do ----------------------------------------------------
    async def _color_action(self, device_id: str, color: Json, fade: float) -> Json:
        """The state of one light for one color of the palette, limited to what the light can do."""
        try:
            capabilities = set((await self._hub.get_device(device_id)).capabilities)
        except DeviceNotFoundError:
            return {"device_id": device_id, "power": True}  # reported as unreachable when applied
        action: Json = {"device_id": device_id, "power": True}
        if color.get("hex_color") and Capability.COLOR.value in capabilities:
            action["hex_color"] = color["hex_color"]
        elif color.get("color_temp_kelvin") and Capability.COLOR_TEMP.value in capabilities:
            action["color_temp_kelvin"] = color["color_temp_kelvin"]
        if color.get("brightness") is not None and Capability.BRIGHTNESS.value in capabilities:
            action["brightness"] = color["brightness"]
        if fade > 0 and len(action) > 2:
            action["transition_time"] = fade
        return action

    async def _is_bulb(self, device_id: str) -> bool:
        """A light that can take a color of the palette (a socket has nothing to color)."""
        try:
            capabilities = set((await self._hub.get_device(device_id)).capabilities)
        except DeviceNotFoundError:
            return True  # kept so the scene reports it as not answering
        colors = {Capability.BRIGHTNESS.value, Capability.COLOR.value, Capability.COLOR_TEMP.value}
        return Capability.ON_OFF.value in capabilities and bool(capabilities & colors)

    async def _split(self, scene: SceneOut) -> tuple[list[str], list[str]]:
        """The devices of the target: (the lights that follow the palette, the ones switched on or off).
        A light listed in `switches` does not take a color. A socket that is not listed is left alone."""
        assert scene.target is not None
        devices = await self._target_devices(scene.target)
        bulbs = [d for d in devices if d not in scene.switches and await self._is_bulb(d)]
        return bulbs, [d for d in devices if d in scene.switches]

    async def _profiles(self, scene: SceneOut, bulbs: list[str]) -> dict[str, tuple[list[Json], bool]]:
        """For each light of an animated scene: its palette, as it can show it, and whether it does color."""
        profiles: dict[str, tuple[list[Json], bool]] = {}
        for device_id in bulbs:
            try:
                capabilities = set((await self._hub.get_device(device_id)).capabilities)
            except DeviceNotFoundError:
                capabilities = set()
            can_color = Capability.COLOR.value in capabilities
            can_white = Capability.COLOR_TEMP.value in capabilities
            profiles[device_id] = (color_path.for_light(scene.palette, can_color, can_white), can_color)
        return profiles

    async def _actions_at(self, scene: SceneOut, bulbs: list[str], step: int) -> list[Json]:
        """The actions of a palette scene. Light number i starts on color i and moves one color
        further at every step (`step` is 0 for a static scene), so the lights are out of phase."""
        profiles = await self._profiles(scene, bulbs) if scene.animated else {}
        actions = []
        for index, device_id in enumerate(bulbs):
            palette = profiles[device_id][0] if device_id in profiles else scene.palette
            color = palette[(scene.assignments.get(device_id, index) + step) % len(palette)]
            actions.append(await self._color_action(device_id, color, self._timing(scene)[1]))
        return actions

    @staticmethod
    def _switch_actions(scene: SceneOut, switched: list[str]) -> list[Json]:
        return [{"device_id": d, "power": scene.switches[d]} for d in switched]

    async def resolve_actions(self, scene: SceneOut) -> list[Json]:
        """The state of each device. A room/group scene is worked out now, so it follows the
        lights that were added to or removed from the room/group since it was saved."""
        if scene.target is None:
            return scene.actions
        bulbs, switched = await self._split(scene)
        return await self._actions_at(scene, bulbs, 0) + self._switch_actions(scene, switched)

    # --- sending -----------------------------------------------------------------
    async def _send(self, action: Json, transition: float | None, source: str) -> bool:
        fade = action.get("transition_time", 0)
        if transition is not None and action.get("power") is not False:
            fade = transition
        command = LightCommand(
            power=action.get("power"),
            brightness=action.get("brightness"),
            hue=action.get("hue"),
            saturation=action.get("saturation"),
            hex_color=action.get("hex_color"),
            color_temp_kelvin=action.get("color_temp_kelvin"),
            transition_time=fade,
            skip_same_level=source == ANIMATION_SOURCE,
        )
        try:
            return await self._hub.set_light(action["device_id"], command, source=source)
        except DeviceNotFoundError:
            return False

    async def _send_all(
        self, actions: list[Json], transition: float | None, source: str, max_wait: float | None = None
    ) -> dict[str, bool]:
        """`max_wait` stops waiting for a lamp that does not answer (the radio retries for a minute), so
        that one lost lamp does not hold back the others."""

        async def send(action: Json) -> bool:
            if max_wait is None:
                return await self._send(action, transition, source)
            try:
                return await asyncio.wait_for(self._send(action, transition, source), max_wait)
            except TimeoutError:
                logger.warning("%s did not answer within %.0f s, skipped", action["device_id"], max_wait)
                return False

        results = await asyncio.gather(*(send(a) for a in actions))
        return {a["device_id"]: ok for a, ok in zip(actions, results, strict=True)}

    @staticmethod
    def _fade_of(action: Json, transition: float | None) -> float:
        fade = action.get("transition_time", 0)
        if transition is not None and action.get("power") is not False:
            fade = transition
        return float(fade)

    async def _changes_both(self, action: Json) -> bool:
        """A lit light whose brightness and color both change."""
        if "brightness" not in action or not any(k in action for k in ("hex_color", "color_temp_kelvin", "hue")):
            return False
        try:
            state = (await self._hub.get_device(action["device_id"])).state
        except DeviceNotFoundError:
            return False
        return state.power is True and state.brightness != action["brightness"]

    async def _send_phased(
        self, actions: list[Json], transition: float | None, source: str, max_wait: float | None = None
    ) -> dict[str, bool]:
        """Send the actions, the brightness before the color on a lit light that changes both.
        Two glide commands sent one after the other to a lamp make it end the first at once: the color would
        jump while the brightness glides. So the brightness glides first, and the color glides once it is done."""
        now: list[Json] = []
        later: list[tuple[Json, float]] = []
        wait = 0.0
        for action in actions:
            fade = self._fade_of(action, transition)
            if fade > 0 and await self._changes_both(action):
                half = fade / 2
                wait = max(wait, half + GUARD)
                level = {"device_id": action["device_id"], "power": True, "brightness": action["brightness"]}
                now.append({**level, "transition_time": half})
                later.append((action, fade))
            else:
                now.append({**action, "transition_time": fade})
        results = await self._send_all(now, None, source, max_wait)
        if later:
            await self._sleep(wait)
            colors = [
                {**{k: v for k, v in a.items() if k != "brightness"}, "transition_time": max(fade - wait, 0.0)}
                for a, fade in later
            ]
            for device_id, ok in (await self._send_all(colors, None, source, max_wait)).items():
                results[device_id] = results.get(device_id, True) and ok
        return results

    async def apply(self, scene_id: int, transition: float | None = None) -> dict[str, bool]:
        """Apply every action at once. Maps device id -> did it acknowledge.
        `transition` (seconds) replaces the fade of the actions that change a light.
        An animated scene starts looping: the result is the one of its first step."""
        scene = await self.get(scene_id)
        if scene.animated:
            return await self._start_animation(scene)
        return await self._send_phased(await self.resolve_actions(scene), transition, "scene")

    # --- animated scenes ---------------------------------------------------------
    async def _on_command(self, device_id: str, source: str) -> None:
        if source == ANIMATION_SOURCE:
            return
        for scene_id, lights in list(self._lights_of.items()):
            if device_id in lights:
                logger.info("Animated scene %s stopped by a command on %s", scene_id, device_id)
                await self.stop(scene_id)

    async def stop(self, scene_id: int) -> bool:
        """Stop an animated scene, even while it is still sending its first step or waiting in the radio
        queue. The lights stay on the color they have."""
        cancelled = await self._cancel(scene_id)  # before the database: a start must not mark it running again
        async with self._sessions() as session:
            scene = await SceneRepository(session).get(scene_id)
            if scene is None:
                raise NotFoundError(f"Unknown scene {scene_id}")
            scene.running = False
            await session.commit()
        return cancelled

    async def _start_animation(self, scene: SceneOut, persist: bool = True) -> dict[str, bool]:
        bulbs, switched = await self._split(scene)
        first: asyncio.Future[dict[str, bool]] = asyncio.get_running_loop().create_future()
        # One start or stop at a time per scene, and the task is registered before anything is sent: a stop
        # (or another start) always finds it, whatever the radio is doing.
        async with self._locks.setdefault(scene.id, asyncio.Lock()):
            await self._cancel(scene.id)
            self._tasks[scene.id] = asyncio.ensure_future(self._run(scene, bulbs, switched, persist, first))
        first.add_done_callback(lambda f: f.cancelled() or f.exception())  # never "exception was never retrieved"
        try:
            return await asyncio.wait_for(asyncio.shield(first), START_WAIT)
        except TimeoutError:
            return {}  # still sending: nothing is known yet, the request is not held for it

    async def _run(
        self,
        scene: SceneOut,
        bulbs: list[str],
        switched: list[str],
        persist: bool,
        first: asyncio.Future[dict[str, bool]],
    ) -> None:
        try:
            # sent as a plain scene: it stops the animated scenes that share these lights.
            # The sockets and the lights to switch are set once, here: only the bulbs loop.
            actions = await self._actions_at(scene, bulbs, 0) + self._switch_actions(scene, switched)
            results = await self._send_phased(actions, None, "scene", STEP_TIMEOUT)
            if persist:
                async with self._sessions() as session:
                    row = await SceneRepository(session).get(scene.id)
                    if row is not None:
                        row.running = True
                        await session.commit()
            self._lights_of[scene.id] = {*bulbs, *switched}
            first.set_result(results)
        except BaseException as e:
            if not first.done():
                if isinstance(e, Exception):
                    first.set_exception(e)
                else:  # cancelled by a stop: nobody is left waiting for the first step
                    first.set_result({})
            if isinstance(e, Exception):
                logger.error("Animated scene %s could not start: %s", scene.id, str(e) or type(e).__name__)
                if self._tasks.get(scene.id) is asyncio.current_task():
                    self._tasks.pop(scene.id, None)  # nothing is running: do not look as if it were
                return
            raise
        await self._animate(scene, bulbs)

    @staticmethod
    def _ends(
        scene: SceneOut, profile: tuple[list[Json], bool], index: int, device_id: str, step: int
    ) -> tuple[Json, Json]:
        """The color a light leaves and the one it reaches at this step."""
        palette = profile[0]
        base = scene.assignments.get(device_id, index)
        return palette[(base + step - 1) % len(palette)], palette[(base + step) % len(palette)]

    async def _animate(self, scene: SceneOut, lights: list[str]) -> None:
        """A timeline, not "send, then wait": the time a command takes does not add up.
        Each change of color is a glide of `fade` seconds, cut in a few steps (see color_path) so that it is
        gentle whatever the two colors. A glide is shorter than its slot by GUARD and the next command goes out
        when the slot ends: a lamp is never sent anything while it is still gliding."""
        profiles = await self._profiles(scene, lights)
        duration, fade = self._timing(scene)
        origin = self._clock()
        step = 1
        while True:
            parts = max(
                color_path.segments(*self._ends(scene, profiles[d], i, d, step), fade, profiles[d][1])
                for i, d in enumerate(lights)
            )
            length = fade / parts
            for part in range(1, parts + 1):
                due = origin + step * duration + (part - 1) * length
                delay = due - self._clock()
                if delay < 0:  # we fell behind (slow radio): the rest follows later, no burst
                    origin -= delay
                    delay = 0.0
                await self._sleep(delay)
                started = self._clock()
                try:
                    actions = []
                    for i, d in enumerate(lights):
                        a, b = self._ends(scene, profiles[d], i, d, step)
                        point = color_path.waypoint(a, b, part / parts, profiles[d][1])
                        actions.append(await self._color_action(d, point, length - GUARD))
                    await self._send_all(actions, None, ANIMATION_SOURCE, max_wait=max(length, STEP_TIMEOUT))
                except Exception:
                    logger.exception("Animated scene %s: step failed", scene.id)
                took = self._clock() - started
                if took > SLOW_COMMAND:
                    logger.warning(
                        "Animated scene %s: a step took %.1f s to be acknowledged, the glides may stop and start. "
                        "Fewer lights in the scene, or a slower speed, helps",
                        scene.id,
                        took,
                    )
                else:
                    logger.debug("Animated scene %s step %s.%s: sent in %.2f s", scene.id, step, part, took)
            step += 1

    async def _cancel(self, scene_id: int) -> bool:
        self._lights_of.pop(scene_id, None)
        task = self._tasks.pop(scene_id, None)
        if task is None:
            return False
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return True

    async def restore(self) -> None:
        """Resume the animated scenes that were running before the restart."""
        async with self._sessions() as session:
            scenes = [SceneOut.model_validate(s) for s in await SceneRepository(session).list_all() if s.running]
        for scene in scenes:
            try:
                await self._start_animation(scene, persist=False)
            except NotFoundError:
                logger.warning("Animated scene %s: its room or group no longer exists", scene.id)

    async def shutdown(self) -> None:
        for scene_id in list(self._tasks):
            await self._cancel(scene_id)  # they stay marked as running, to resume at the next start
