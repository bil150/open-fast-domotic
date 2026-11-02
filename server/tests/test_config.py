from app.core import config
from app.core.config import Settings


def settings(*files, **values) -> Settings:
    return Settings(_env_file=files or None, **values)


def test_data_is_in_persistence_on_a_machine(monkeypatch):
    monkeypatch.setattr(config, "in_container", lambda: False)
    s = settings()
    assert s.data_path == "./persistence"
    assert s.zigbee_db_path.replace("\\", "/") == "./persistence/app.db"


def test_data_is_on_the_volume_in_a_container_even_without_a_env(monkeypatch):
    monkeypatch.setattr(config, "in_container", lambda: True)
    s = settings()
    assert s.data_path == "/data"
    assert s.zigbee_db_path.replace("\\", "/") == "/data/app.db"


def test_explicit_places_win_over_the_container_default(monkeypatch):
    monkeypatch.setattr(config, "in_container", lambda: True)
    assert settings(data_dir="/elsewhere").data_path == "/elsewhere"
    assert settings(db_path="/db/app.db").data_path == "/db"


def test_env_local_wins_over_env(tmp_path):
    env = tmp_path / ".env"
    local = tmp_path / ".env.local"
    env.write_text("Z_DONGLE_PATH=/dev/ttyUSB0\nZ_DONGLE_BAUDRATE=57600\nTZ=UTC\n", encoding="utf-8")
    local.write_text("Z_DONGLE_PATH=COM4\n", encoding="utf-8")
    s = settings(env, local)
    assert s.z_dongle_path == "COM4"  # the machine's own value
    assert s.z_dongle_baudrate == 57600  # shared value kept


def test_missing_env_files_are_fine(tmp_path):
    assert settings(tmp_path / ".env", tmp_path / ".env.local").z_dongle_path == "/dev/ttyUSB0"
