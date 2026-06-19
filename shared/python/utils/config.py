"""
PossKassa — Umumiy konfiguratsiya sozlamalari
Pydantic Settings orqali .env fayldan o'qish
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Ma'lumotlar bazasi ───────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://posskassa:secret@localhost:5432/posskassa"
    DB_ECHO: bool = False

    # ─── Redis ───────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── RabbitMQ ────────────────────────────────────
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # ─── MinIO / S3 ──────────────────────────────────
    S3_ENDPOINT:    str = "http://localhost:9000"
    S3_ACCESS_KEY:  str = "minioadmin"
    S3_SECRET_KEY:  str = "minioadmin"
    S3_BUCKET:      str = "posskassa"

    # ─── Keycloak / JWT ──────────────────────────────
    KEYCLOAK_URL:           str = "http://localhost:8080"
    KEYCLOAK_REALM:         str = "posskassa"
    KEYCLOAK_CLIENT_ID:     str = "posskassa-api"
    KEYCLOAK_CLIENT_SECRET: str = "change-me"
    JWT_ALGORITHM:          str = "RS256"
    JWT_PUBLIC_KEY:         str = ""   # PEM format, .env da to'ldiriladi

    # ─── Tashqi integratsiyalar ───────────────────────
    OFD_API_URL:      str = "https://ofd.soliq.uz/api"
    OFD_TOKEN:        str = ""
    DIDOX_API_URL:    str = "https://api.didox.uz/v1"
    DIDOX_TOKEN:      str = ""
    EIMZO_API_URL:    str = "https://eimzo.uz/api"
    ESKIZ_EMAIL:      str = ""
    ESKIZ_PASSWORD:   str = ""
    ANTHROPIC_API_KEY: str = ""  # Claude Vision uchun (Intake moduli)

    # ─── Ilova sozlamalari ────────────────────────────
    APP_ENV:          str = "development"
    SECRET_KEY:       str = "super-secret-change-in-production"
    CORS_ORIGINS:     list[str] = ["http://localhost:3000", "http://localhost:3001"]
    LOG_LEVEL:        str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
