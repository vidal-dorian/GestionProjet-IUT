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
    # Adresses e-mail (séparées par des virgules) promues administrateur à
    # leur prochaine connexion. Un compte promu le reste même s'il est retiré
    # de la liste (le retrait se fait alors en base).
    admin_emails: str = ""
    auto_create_schema: bool = True
    enable_background_sync: bool = True

    @property
    def admin_email_set(self) -> set[str]:
        return {email.strip().lower() for email in self.admin_emails.split(",") if email.strip()}


settings = Settings()
