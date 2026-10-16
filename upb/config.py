import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://virtual.ipb.pt"

load_dotenv()


@dataclass
class Config:
    username: str
    password: str
    base_url: str


def load_config() -> Config:
    username = os.environ.get("UPB_USERNAME", "").strip()
    password = os.environ.get("UPB_PASSWORD", "").strip()
    base_url = os.environ.get("UPB_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")

    if not username or not password:
        raise RuntimeError(
            "UPB_USERNAME and UPB_PASSWORD are required. "
            "Copy .env.example to .env and fill them in."
        )
    return Config(username=username, password=password, base_url=base_url)
