import pytest

from upb import config
from upb.config import Config, load_config


@pytest.fixture
def clean_env(monkeypatch):
    for var in ("UPB_USERNAME", "UPB_PASSWORD", "UPB_BASE_URL"):
        monkeypatch.delenv(var, raising=False)


def test_load_config_success(monkeypatch, clean_env):
    monkeypatch.setenv("UPB_USERNAME", "  user@ipb.pt  ")
    monkeypatch.setenv("UPB_PASSWORD", "  secret  ")
    monkeypatch.setenv("UPB_BASE_URL", "https://virtual.ipb.pt/")
    assert load_config() == Config(
        username="user@ipb.pt",
        password="secret",
        base_url="https://virtual.ipb.pt",
    )


def test_load_config_default_base_url(monkeypatch, clean_env):
    monkeypatch.setenv("UPB_USERNAME", "u")
    monkeypatch.setenv("UPB_PASSWORD", "p")
    assert load_config().base_url == config.DEFAULT_BASE_URL


def test_load_config_missing_username(monkeypatch, clean_env):
    monkeypatch.setenv("UPB_PASSWORD", "p")
    with pytest.raises(RuntimeError, match="UPB_USERNAME and UPB_PASSWORD"):
        load_config()


def test_load_config_missing_password(monkeypatch, clean_env):
    monkeypatch.setenv("UPB_USERNAME", "u")
    with pytest.raises(RuntimeError, match="UPB_USERNAME and UPB_PASSWORD"):
        load_config()
