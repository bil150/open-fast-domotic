import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The one .env, at the root of the project: shared with docker compose and the client.
ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (ROOT / ".env",)


def in_container() -> bool:
    """Docker and Podman leave one of these files in every container."""
    return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables / the .env at the root of the project."""

    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    z_dongle_path: str = "/dev/ttyUSB0"
    z_dongle_baudrate: int = 115200
    # zigpy database (radio network key + paired devices). Historical name and
    # variable kept so that an existing network is not re-formed.
    db_path: str = ""
    # Folder holding every file written by the server (databases, logs). Default: /data in a container,
    # ./persistence elsewhere.
    data_dir: str = ""
    # Start the radio. Disabled by the tests, which use a fake coordinator.
    enable_z: bool = True
    # Resume the light animations that were running before a restart.
    restore_animations: bool = True
    cors_origins: str = "*"
    # Folder of the built client to serve (set by the Docker image).
    static_dir: str = ""
    version: str = "0.1.0"

    @property
    def data_path(self) -> str:
        if self.data_dir:
            return self.data_dir
        if self.db_path:
            return os.path.dirname(self.db_path) or "."
        # in a container the data is on the volume, whatever the .env says (or does not say)
        return "/data" if in_container() else "./persistence"

    @property
    def z_db_path(self) -> str:
        return self.db_path or os.path.join(self.data_path, "app.db")

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{os.path.join(self.data_path, 'domotic.db')}"

    @property
    def log_file(self) -> str:
        return os.path.join(self.data_path, "open-fast-domotic.log")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
