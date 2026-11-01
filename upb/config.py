import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://virtual.ipb.pt"
DEFAULT_GCAL_CREDENTIALS = "credentials.json"
DEFAULT_GCAL_TOKEN = "token.json"
DEFAULT_GCAL_CALENDAR_NAME = "IPB.Virtual"

load_dotenv()


@dataclass
class Config:
    username: str
    password: str
    base_url: str
    gcal_credentials: str = DEFAULT_GCAL_CREDENTIALS
    gcal_token: str = DEFAULT_GCAL_TOKEN
    gcal_calendar_id: str = ""
    gcal_calendar_name: str = DEFAULT_GCAL_CALENDAR_NAME


def load_config() -> Config:
    username = os.environ.get("UPB_USERNAME", "").strip()
    password = os.environ.get("UPB_PASSWORD", "").strip()
    base_url = os.environ.get("UPB_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")

    if not username or not password:
        raise RuntimeError(
            "UPB_USERNAME and UPB_PASSWORD are required. "
            "Copy .env.example to .env and fill them in."
        )
    return Config(
        username=username,
        password=password,
        base_url=base_url,
        gcal_credentials=os.environ.get("UPB_GCAL_CREDENTIALS", DEFAULT_GCAL_CREDENTIALS).strip(),
        gcal_token=os.environ.get("UPB_GCAL_TOKEN", DEFAULT_GCAL_TOKEN).strip(),
        gcal_calendar_id=os.environ.get("UPB_GCAL_CALENDAR_ID", "").strip(),
        gcal_calendar_name=os.environ.get("UPB_GCAL_CALENDAR_NAME", DEFAULT_GCAL_CALENDAR_NAME).strip(),
    )
