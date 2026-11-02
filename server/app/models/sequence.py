from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Json
from app.db.base import Base


class Sequence(Base):
    __tablename__ = "sequences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    # ordered list of {scene_id, duration}: apply the scene, hold it `duration` seconds
    steps: Mapped[list[Json]] = mapped_column(JSON)
    loop: Mapped[bool] = mapped_column(default=True)
    enabled: Mapped[bool] = mapped_column(default=True)
