from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "mysql+pymysql://gestionprojet:gestionprojet@localhost:3306/gestionprojet"
    cors_origins: str = "http://localhost:5173"


settings = Settings()
