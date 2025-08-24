try:
    # pydantic v2 moved BaseSettings to pydantic-settings package
    from pydantic_settings import BaseSettings
except Exception:
    # fall back for older environments
    from pydantic import BaseSettings


class Settings(BaseSettings):
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "master"
    KEYCLOAK_CLIENT_ID: str = "institution-client"

    DATABASE_URL: str = "sqlite:///./institution_manager.db"
    # If True, Keycloak auth is bypassed (for tests/dev). When enabled, the app will accept a header
    # X-Test-User: <user_id> to act as that user. Use only in tests/dev.
    KEYCLOAK_BYPASS: bool = False

    # When True, deleting a type (activity/space/stock) will cascade by setting references to NULL
    # or deleting children as appropriate. Default is False (prevent deletion if referenced).
    TYPE_CASCADE_DELETE: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
