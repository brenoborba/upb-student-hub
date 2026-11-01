from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./upb_hub.db"
    encryption_key: str = ""
    cors_origins: str = "*"

    # Google OAuth app used to mint per-user refresh tokens.
    google_client_id: str = ""
    google_client_secret: str = ""

    # Default Sakai instance (per-user override stored on credentials).
    sakai_base_url: str = "https://virtual.ipb.pt"


def get_settings() -> Settings:
    return Settings()
