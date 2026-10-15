# agent-frontend

Panel de **La Brasa** (agente de voz Sofía): llamada en vivo con transcripción, pedidos (Kanban), reservas, historial de llamadas y menú.
React 19 + Vite + TypeScript + Tailwind v4 + shadcn/ui. Gestor: **pnpm**.

## Uso

```bash
cp .env.example .env     # VITE_API_URL apunta al agent-backend (http://localhost:8000)
pnpm install
pnpm dev                 # http://localhost:5173
```

| Script | Qué hace |
|---|---|
| `pnpm build` | typecheck + build de producción |
| `pnpm lint` / `pnpm typecheck` | ESLint / TypeScript |
| `pnpm test` | tests unitarios (Vitest) |
| `pnpm test:e2e` | tests E2E (Playwright, requiere el backend con datos seed) |

## Estructura

- `src/features/` — `call`, `orders`, `reservations`, `calls`, `menu`, `system` (detector de cold-start)
- `src/lib/` — cliente API tipado, sesión `X-Session-Id`
- `src/components/ui/` — componentes shadcn/ui

El frontend no necesita claves de Vapi/Retell: las obtiene de `POST /voice/web-call` del backend.
Plan y estado: [`../docs/10-frontend-fases.md`](../docs/10-frontend-fases.md) · UX: [`../docs/04-frontend-ux.md`](../docs/04-frontend-ux.md).
