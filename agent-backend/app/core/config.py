from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


def normalize_database_url(url: str) -> str:
    """Acepta la URL tal como la entrega Neon (`postgresql://...?sslmode=require&channel_binding=require`)
    y la convierte a la de asyncpg: driver `+asyncpg`, `ssl=` en vez de `sslmode=`, y sin
    `channel_binding` (asyncpg no lo admite). Otras URLs (p. ej. ya normalizadas) quedan igual."""
    parsed = make_url(url)
    if parsed.get_backend_name() not in ("postgresql", "postgres"):
        return url
    query = dict(parsed.query)
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    query.pop("channel_binding", None)
    parsed = parsed.set(drivername="postgresql+asyncpg", query=query)
    return parsed.render_as_string(hide_password=False)


def is_pooled(url: str) -> bool:
    """El endpoint pooled de Neon (pgbouncer en modo transacción) lleva `-pooler` en el host."""
    return "-pooler" in (make_url(url).host or "")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/speaker_agent"
    database_url_test: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/speaker_agent_test"
    )
    # Conexión directa (sin pooler) para migraciones; si está vacía se usa `database_url`.
    database_url_direct: str = ""
    # None = autodetectar (host con `-pooler`, como Neon). True/False fuerza el modo para otros pgbouncer.
    db_pooled: bool | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # Observabilidad
    environment: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    release: str = ""
    # SOLO desarrollo: guarda los payloads de Vapi/Retell para convertirlos en fixtures (contienen datos
    # personales de las llamadas). Vacío = desactivado.
    capture_payloads_dir: str = ""
    # Proveedor de voz activo para el frontend. Las rutas /vapi/* y /retell/* existen siempre.
    voice_provider: Literal["vapi", "retell"] = "vapi"
    vapi_webhook_secret: str = "change-me"
    vapi_public_key: str = ""
    vapi_assistant_id: str = ""
    retell_api_key: str = ""
    retell_agent_id: str = ""
    retell_api_base: str = "https://api.retellai.com"
    frontend_origin: str = "http://localhost:5173"
    timezone: str = "America/La_Paz"
    currency: str = "BOB"
    restaurant_open: str = "12:00"
    restaurant_close: str = "23:00"
    max_party_size: int = 12
    reservation_min_lead_minutes: int = 30
    reservation_last_seating_minutes_before_close: int = 60
    reservation_max_days_ahead: int = 60
    # Límites (formato slowapi). `web_call_daily_cap` es global; 0 lo desactiva.
    rate_limit_panel: str = "120/minute"
    rate_limit_write: str = "30/minute"
    rate_limit_web_call: str = "5/minute;30/hour"
    web_call_daily_cap: int = 200
    # Retención de datos de visitantes (la sesión demo no se borra). Intervalo 0 = sin tarea interna.
    data_retention_days: int = 7
    cleanup_interval_hours: int = 6
    prep_minutes_pickup: int = 20
    prep_minutes_delivery: int = 40

    @field_validator("database_url", "database_url_test", "database_url_direct")
    @classmethod
    def _normalize_url(cls, v: str) -> str:
        return normalize_database_url(v) if v else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
