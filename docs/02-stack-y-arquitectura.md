# 2. Stack y arquitectura

## Arquitectura

```
[Navegador: React + Vapi Web SDK] --voz--> [Vapi: STT + LLM + TTS]
        |                                        |
        | REST (panel, SSE/polling)              | tool calls + server messages (HTTPS POST)
        v                                        v
                      [FastAPI (pública)]
                        routers/vapi   (tools + webhook)
                        routers/panel  (orders, reservations, calls, menu)
                        services/*
                              v
                      [PostgreSQL (Neon)]
```

## Frontend

| Tema | Elección | Nota |
|---|---|---|
| Build | Vite + React 19 + TypeScript estricto | SPA; Next.js sería excesivo |
| Rutas | TanStack Router | tipado, encaja con Query |
| Datos | TanStack Query v5 | `refetchInterval` dinámico + `invalidateQueries` |
| Estilos | Tailwind v4 + shadcn/ui | componentes base de shadcn |
| Animación | Motion | orbe de voz, entrada de pedidos |
| Estado local | Zustand | llamada, transcripción, mute |
| Validación | Zod | respuestas del API |
| Tipos del API | openapi-typescript + openapi-fetch | generados desde el OpenAPI de FastAPI (`pnpm gen:api`) |
| Toasts / iconos | Sonner / Lucide | |
| Fechas | date-fns | |
| Mocks | MSW | desarrollar sin backend |
| Tests | Vitest + Testing Library; Playwright (1 flujo de humo) | |
| Calidad | Biome | lint + formato |
| Voz | `@vapi-ai/web` **y** `retell-client-js-sdk` (carga diferida, un adaptador por proveedor) | |
| Hosting | Vercel | |

## Backend

| Capa | Elección | Nota |
|---|---|---|
| API | FastAPI + Uvicorn | |
| Validación / config | Pydantic v2 + pydantic-settings | `get_settings()` con `lru_cache` |
| BD | PostgreSQL (Neon) | `ssl=require`; con pooler: `statement_cache_size=0` |
| ORM | SQLAlchemy 2.x async + asyncpg | |
| Migraciones | Alembic | |
| Rate limit | slowapi (cableado de verdad) | |
| Logs | structlog (JSON, con `call_id`) | |
| Errores | Sentry (plan gratis) | también en frontend |
| Paquetes | uv (con lockfile) | |
| Calidad | Ruff (+ pyright o mypy) | |
| Tests | pytest + pytest-asyncio + httpx + testcontainers (Postgres real) | no SQLite: `JSONB`/`UUID` |
| Túnel dev | ngrok o Cloudflare Tunnel | Vapi necesita URL pública |
| Hosting | Fly.io o Railway (Dockerfile) | Render gratis tiene cold start de ~30 s; si se usa, ping externo |

## Proveedor de voz intercambiable (Vapi / Retell)
```
Frontend --POST /voice/web-call--> Backend --(Retell: create-web-call)--> Retell
   |  provider = vapi | retell                       (Vapi: clave pública + assistantId)
   v
 VoiceAdapter (VapiAdapter | RetellAdapter)  ← misma interfaz: start/stop/mute + eventos normalizados
Proveedor --tools/webhooks--> /vapi/*  o  /retell/*  --> tool_runner --> servicios --> PostgreSQL
```
Se elige con `VOICE_PROVIDER` (backend). El frontend no necesita variables de Vapi/Retell: obtiene todo de `/voice/web-call`.

## Qué NO usar
Next.js, Redux, GraphQL, WebSockets propios (usar polling o SSE), microservicios, colas.
