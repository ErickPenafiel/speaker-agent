"""Logging estructurado. Todo (structlog y stdlib, incluido uvicorn) sale por un único handler,
en JSON en producción y legible en desarrollo. Regla: no se registran datos de clientes
(nombres, direcciones, transcripciones), ni headers (X-Session-Id es una credencial), ni query strings."""

import logging
import sys
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = structlog.get_logger("http")

QUIET_PATHS = {"/health", "/health/ready"}  # se registran en DEBUG para no llenar los logs


class _StderrHandler(logging.StreamHandler):
    """Escribe en el `sys.stderr` vigente en cada emisión (no el de cuando se creó el handler)."""

    @property
    def stream(self):  # type: ignore[override]
        return sys.stderr

    @stream.setter
    def stream(self, value) -> None:
        pass


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )
    renderer = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )
    handler = _StderrHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,  # logs de librerías (uvicorn, sqlalchemy...) con el mismo formato
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    # El access log de uvicorn incluye la query string; ya registramos cada petición sin ella.
    logging.getLogger("uvicorn.access").disabled = True


class RequestContextMiddleware:
    """Asigna un `request_id` (nunca el que mande el cliente: evita inyección en logs), lo devuelve en
    `X-Request-Id`, lo enlaza a todos los logs de la petición y registra método, ruta, estado y duración."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:12]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        status = 500
        start = time.perf_counter()

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-Id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            path = scope.get("path", "")
            emit = log.debug if path in QUIET_PATHS else log.info
            emit(
                "request",
                method=scope.get("method"),
                path=path,  # sin query string
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000),
            )
            structlog.contextvars.clear_contextvars()
