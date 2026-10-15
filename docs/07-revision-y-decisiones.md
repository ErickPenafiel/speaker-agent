# 7. Revisión de los documentos originales y decisiones

Originales en `docs/origen/`. Estos son los problemas detectados y cómo se resolvieron en este plan.

## Errores e inconsistencias
| Problema | Decisión |
|---|---|
| El video decía "NestJS" pero el backend es FastAPI | Stack del video: Vapi, FastAPI, PostgreSQL, React |
| Rutas `/:id` (estilo Nest) vs `{id}` | Rutas FastAPI `{id}`; tipos generados desde OpenAPI |
| Backend remite a `backend-voz.md` (ausente) | Plan autocontenido en `docs/`; falta escribir el prompt de Sofía, el menú y los 12 guiones de prueba |
| `number` con `autoincrement=True` no-PK | `Identity()`/`Sequence` |
| `arguments` puede ser string JSON | `json.loads` si es `str` |
| Idempotencia "buscar y luego insertar" (carrera) | unique + `IntegrityError`; también en reservas |
| Sesión de BD compartida en el bucle de tools | transacción por tool call + `rollback` |
| `BackgroundTasks` con la sesión de la petición | sesión propia en la tarea |
| `slowapi` listado pero sin cablear | cablearlo (Limiter + handler + middleware) |
| Dockerfile roto (solo `pyproject.toml`, puerto fijo, root) | `uv sync --frozen`, `$PORT`, usuario no root (hecho) |
| `uv add` sin deps de test | añadidas como dev (hecho) |
| Neon + asyncpg | `ssl=require`; pooler → `statement_cache_size=0` |
| "bolivianos" fijo en el código | `currency` en `Settings` |
| "Zustand o useReducer" | Zustand |
| Refresco esperaba al reporte final | invalidar pedidos al resultado de la tool |
| Solo Chrome/Edge sugerido | probar Safari iOS |
| Criterios vagos ("pocos segundos") | números en `docs/06` |

## Decisiones de producto
- Agente EN/ES (el cliente puede no hablar español).
- Pedido visible en la misma pantalla de la llamada.
- Datos aislados por sesión; límites de gasto en Vapi.
- Hosting: Fly.io/Railway preferido sobre Render gratis (cold start).
- Menú (pantalla E) = prioridad baja.
- **Proveedor de voz intercambiable (Vapi/Retell)**: rutas de ambos siempre montadas, activo por `VOICE_PROVIDER`, adaptador en el frontend, `tool_runner` compartido. Firma de Retell implementada en el propio código (esquema del SDK oficial) en vez de añadir `retell-sdk`.

## Pendiente de verificar con la documentación oficial de Vapi
Formato actual de tool calls y server messages, nombre del header del secreto, evento `volume-level` y `metadata` en `start()`, opciones `maxDurationSeconds`/`silenceTimeoutSeconds`.
