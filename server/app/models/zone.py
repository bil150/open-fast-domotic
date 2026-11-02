from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Zone(Base):
    """A named set of devices that scenes and effects can target."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    device_ids: Mapped[list[str]] = mapped_column(JSON)


class Room(Zone):
    """A fixed zone of the home (Living room...). A device belongs to at most one room."""

    __tablename__ = "rooms"


class Group(Zone):
    """A free set of devices (Spots...). A device can be in several groups."""

    __tablename__ = "groups"
