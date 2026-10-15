import datetime as dt

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Por IP. Detrás de un proxy (Render, Fly, Railway) hay que arrancar uvicorn con --proxy-headers
# para que la IP real sea la del cliente y no la del proxy.
limiter = Limiter(key_func=get_remote_address)


# Callables: slowapi los evalúa en cada petición, así la configuración se lee de Settings.
def panel_limit() -> str:
    return get_settings().rate_limit_panel


def write_limit() -> str:
    return get_settings().rate_limit_write


def web_call_limit() -> str:
    return get_settings().rate_limit_web_call


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    try:
        retry_after = int(exc.limit.limit.get_expiry())
    except AttributeError:
        retry_after = 60
    return JSONResponse(
        {"detail": "Demasiadas peticiones. Intenta de nuevo en unos instantes."},
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )


class DailyCap:
    """Tope global por día (en memoria): válvula de seguridad contra el gasto de crédito.
    Se reinicia con el proceso, lo que para una demo es aceptable."""

    def __init__(self) -> None:
        self._day: dt.date | None = None
        self._count = 0

    def hit(self, limit: int, today: dt.date) -> bool:
        """Registra un uso. False si ya se alcanzó el tope de hoy. `limit <= 0` = sin tope."""
        if limit <= 0:
            return True
        if self._day != today:
            self._day, self._count = today, 0
        if self._count >= limit:
            return False
        self._count += 1
        return True

    def reset(self) -> None:
        self._day, self._count = None, 0


web_call_cap = DailyCap()
