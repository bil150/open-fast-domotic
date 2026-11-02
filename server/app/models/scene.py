from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Json
from app.db.base import Base


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    # Legacy scene: list of {device_id, power, brightness, hue, saturation, hex_color, ...}.
    # Empty for a scene that targets a room or a group (its actions are worked out when it is applied).
    actions: Mapped[list[Json]] = mapped_column(JSON)
    # {type: "room" | "group", id}: the lights of that room/group get the colors of the palette
    target: Mapped[Json | None] = mapped_column(JSON, default=None)
    # list of {hex_color | color_temp_kelvin, brightness}, spread over the lights of the target
    palette: Mapped[list[Json] | None] = mapped_column(JSON, default=None)
    # device id -> index in the palette, for the lights the user placed by hand
    assignments: Mapped[dict[str, int] | None] = mapped_column(JSON, default=None)
    # device id -> on (True) / off (False): sockets, which have no color, and the lights that must be off.
    # A socket that is not listed is left as it is.
    switches: Mapped[dict[str, bool] | None] = mapped_column(JSON, default=None)
    # "fast" | "medium" | "slow": how long the lights take to glide to their color (see app/core/speeds.py).
    # `fade` and `duration` hold the seconds that speed stands for (older scenes: whatever was saved).
    speed: Mapped[str | None] = mapped_column(default=None)
    fade: Mapped[float] = mapped_column(default=0, server_default="0")
    # Animated scene: every light steps to the next color of the palette every `duration` seconds,
    # starting from a different color so they are never all the same at once.
    animated: Mapped[bool] = mapped_column(default=False, server_default="0")
    duration: Mapped[float] = mapped_column(default=5, server_default="5")
    # the animation was running: it is resumed after a restart
    running: Mapped[bool] = mapped_column(default=False, server_default="0")
