from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "mysql+pymysql://gestionprojet:gestionprojet@localhost:3306/gestionprojet"
    cors_origins: str = "http://localhost:5173"
    github_token: str | None = None
    github_sync_interval_minutes: int = 15
    cloudflare_team_domain: str | None = None
    cloudflare_access_aud: str | None = None
    dev_bypass_auth_enabled: bool = False


settings = Settings()
