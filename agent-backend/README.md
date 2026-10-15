# agent-backend

API del agente de voz **Sofía** (La Brasa): tools para Vapi/Retell, webhooks, pedidos, reservas, llamadas y menú.
FastAPI + SQLAlchemy async + Alembic + PostgreSQL. Gestor: **uv**.

## Uso

```bash
docker compose up -d --wait        # Postgres local (desde la raíz del repo)
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m seed.menu         # menú ficticio
uv run python -m seed.demo         # datos de ejemplo del panel
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q
```

Variables de entorno: ver `.env.example` (proveedor activo con `VOICE_PROVIDER=vapi|retell`).

## Estructura

- `app/routers/` — `menu`, `orders`, `reservations`, `calls`, `voice`, `vapi`, `retell`, `health`
- `app/providers/` — adaptadores Vapi/Retell · `app/services/` — lógica (tools, total del pedido)
- `app/db/` — modelos y migraciones · `app/core/` — config, seguridad, límites, logging
- `scripts/start.sh` — arranque del contenedor · `Dockerfile`, `fly.toml` (y `../render.yaml`)

Plan y estado: [`../docs/08-backend-fases.md`](../docs/08-backend-fases.md) · Despliegue: [`../docs/09-despliegue.md`](../docs/09-despliegue.md).
