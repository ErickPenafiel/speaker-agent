import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.limits import limiter, rate_limit_handler
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.observability import init_sentry
from app.jobs.cleanup import cleanup_loop
from app.routers import calls, health, menu, orders, reservations, retell, vapi, voice

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Aquí y no al importar: así los tests y los scripts no reconfiguran el logging global.
    configure_logging(settings.log_level, settings.log_format)
    init_sentry(settings)
    task = None
    if settings.cleanup_interval_hours > 0:
        task = asyncio.create_task(
            cleanup_loop(
                interval_hours=settings.cleanup_interval_hours,
                retention_days=settings.data_retention_days,
            )
        )
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Speaker Agent API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)  # el más externo: envuelve también a CORS

app.include_router(health.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(reservations.router)
app.include_router(calls.router)
app.include_router(vapi.router)
app.include_router(retell.router)
app.include_router(voice.router)
