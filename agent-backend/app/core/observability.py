import sentry_sdk
from sentry_sdk.types import Event, Hint

from app.core.config import Settings

OMITTED = "[omitido: el mensaje de la base de datos puede incluir datos de clientes]"
DB_MODULES = ("sqlalchemy", "asyncpg")


def scrub_event(event: Event, hint: Hint) -> Event:
    """Quita de los eventos de Sentry todo lo que identifica al cliente o es una credencial:
    headers (X-Session-Id, secretos), cuerpo, cookies y query string (queda método y URL), y el
    texto de los errores de base de datos (Postgres adjunta la fila en `DETAIL`)."""
    for exc in (event.get("exception") or {}).get("values", []):
        if str(exc.get("module", "")).startswith(DB_MODULES):
            exc["value"] = OMITTED
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("headers", "data", "cookies", "query_string", "env"):
            request.pop(key, None)
    event.pop("user", None)
    return event


def init_sentry(settings: Settings) -> bool:
    """Activa Sentry solo si hay DSN. False = desactivado."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        max_request_body_size="never",
        before_send=scrub_event,
    )
    return True
