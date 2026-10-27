# Cómo contribuir

1. Haz un fork y crea una rama desde `main`.
2. Backend (`agent-backend/`): `uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest`.
3. Frontend (`agent-frontend/`): `pnpm install && pnpm build`.
4. Abre un pull request describiendo el cambio; el CI debe pasar.
