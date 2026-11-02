from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Json
from app.db.base import Base


class DeviceName(Base):
    """User-chosen name of a device."""

    __tablename__ = "device_names"

    device_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class DeviceMeta(Base):
    """What was probed from a device (color capabilities, white range...)."""

    __tablename__ = "device_meta"

    device_id: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[Json] = mapped_column(JSON)


class Animation(Base):
    """Running light animation, resumed after a restart."""

    __tablename__ = "animations"

    device_id: Mapped[str] = mapped_column(primary_key=True)
    keys: Mapped[list[Json]] = mapped_column(JSON)
