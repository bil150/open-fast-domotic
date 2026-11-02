from sqlalchemy import JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Json
from app.db.base import Base


class ButtonMapping(Base):
    """What a button event triggers: a scene, a toggle or a power change."""

    __tablename__ = "button_mappings"
    __table_args__ = (UniqueConstraint("device_id", "event"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str]
    event: Mapped[str]
    action: Mapped[Json] = mapped_column(JSON)
