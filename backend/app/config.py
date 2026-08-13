from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "mysql+pymysql://gestionprojet:gestionprojet@localhost:3306/gestionprojet"
    cors_origins: str = "http://localhost:5173"
    secret_key: str = "dev-secret-change-me"
    cookie_secure: bool = False
    github_token: str | None = None
    github_sync_interval_minutes: int = 15


settings = Settings()
