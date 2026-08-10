from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://geoai:geoai_secret@localhost:5432/geoai_explorer"
    database_url_sync: str = "postgresql://geoai:geoai_secret@localhost:5432/geoai_explorer"
    stac_api_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    pc_subscription_key: str | None = None
    cache_dir: str = "/app/.cache"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    lst_anomaly_radius_m: float = 5000.0
    max_cloud_cover: float = 30.0


settings = Settings()
