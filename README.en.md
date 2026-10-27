# Speaker Agent

[Español](README.md) · English

Demo **voice agent for a restaurant**: takes orders, makes reservations and transfers to a human. Voice via **Vapi or Retell** (interchangeable), API in **FastAPI**, dashboard in **React**. All data is fictional.

- `agent-backend/` — FastAPI + SQLAlchemy async + Alembic (uv)
- `agent-frontend/` — React 19 + Vite + TypeScript + Tailwind v4 (pnpm)
- `docs/` — planning documents (Spanish)

## Quickstart

```bash
docker compose up -d --wait            # local database
cd agent-backend && cp .env.example .env && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload
cd ../agent-frontend && pnpm install && pnpm dev
```

Check `README.md` and `docs/09-despliegue.md` for provider setup (Vapi/Retell) and deployment.

## Contributing & security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). License: [MIT](LICENSE).
