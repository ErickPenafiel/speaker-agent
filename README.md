# Speaker Agent

Demo de **agente de voz para restaurante** (La Brasa, agente Sofía): toma pedidos, hace reservas y transfiere a una persona. Voz con **Vapi o Retell** (intercambiables), API con **FastAPI**, panel con **React**. Todos los datos son ficticios.

## Estructura

```
speaker-agent/
  agent-backend/     FastAPI + SQLAlchemy async + Alembic (uv)
  agent-frontend/    React 19 + Vite + TypeScript + Tailwind v4 (pnpm)
  docs/       planificación (leer en orden)
    origen/   documentos originales de partida
```

## Documentación

| # | Archivo | Contenido |
|---|---|---|
| 1 | [docs/01-vision-y-alcance.md](docs/01-vision-y-alcance.md) | Objetivo, caso de uso, alcance |
| 2 | [docs/02-stack-y-arquitectura.md](docs/02-stack-y-arquitectura.md) | Librerías elegidas y por qué, diagrama |
| 3 | [docs/03-backend.md](docs/03-backend.md) | Modelo de datos, endpoints, tools de Vapi, webhook |
| 4 | [docs/04-frontend-ux.md](docs/04-frontend-ux.md) | Pantallas, UX/UI, componentes, estados de error |
| 5 | [docs/05-seguridad-y-costos.md](docs/05-seguridad-y-costos.md) | Clave pública de Vapi, privacidad, límites |
| 6 | [docs/06-plan-y-criterios.md](docs/06-plan-y-criterios.md) | Plan por días, tests, criterios de aceptación, video |
| 7 | [docs/07-revision-y-decisiones.md](docs/07-revision-y-decisiones.md) | Problemas detectados en los originales y decisiones |
| 8 | [docs/08-backend-fases.md](docs/08-backend-fases.md) | Plan del backend por fases y su estado |
| 9 | [docs/09-despliegue.md](docs/09-despliegue.md) | Despliegue, configuración de Vapi/Retell, observabilidad y checklist de demo |
| 10 | [docs/10-frontend-fases.md](docs/10-frontend-fases.md) | Plan del frontend por fases, entregables y criterios |

## Arranque rápido

```bash
# Base de datos local
docker compose up -d --wait

# Backend
cd agent-backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m seed.menu
uv run python -m seed.demo     # datos de ejemplo del panel
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q

# Frontend
cd agent-frontend
cp .env.example .env
pnpm install
pnpm dev
```

## Estado

Backend: fases 0–7 completas (esquema, seed, `GET /menu`, tools multi-proveedor **Vapi / Retell**, `/voice/web-call`, `create_order` con total en backend e idempotencia, `GET/PATCH /orders`, `create_reservation`, `transfer_to_human`, `GET /reservations`, webhooks de fin de llamada de Vapi y Retell, `GET /calls` con detalle, panel aislado por visitante con datos de ejemplo, rate limit y limpieza, logs estructurados sin datos personales, Sentry, soporte de Neon/pooler, contenedor, CI y configs de despliegue; 163 tests). **Backend terminado.** Ver `docs/08`.

Frontend: fases 0–6 completas (cliente API tipado, sesión `X-Session-Id`, `VoiceAdapter` para Vapi/Retell, pantalla de llamada en vivo con `VoiceOrb` animado, transcripción en streaming, panel de pedidos en vivo, cocina Kanban con cambio de estado, libro de reservas, historial de llamadas con transcripción completa, modal de menú, diseño responsivo "La Brasa" con dark/light mode, detector de cold-start y suite de tests unitarios; 15 tests pasando, 0 errores de linter). **Frontend terminado.** Ver `docs/10`.

Proveedor de voz: `VOICE_PROVIDER=vapi|retell` en `agent-backend/.env`.
