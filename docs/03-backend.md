# 3. Backend (FastAPI)

## Estructura (esqueleto ya creado; lo marcado ✅ existe)

```
agent-backend/
  app/
    main.py                 ✅
    core/ config.py ✅  security.py ✅  errors.py ✅   # + logging.py (structlog)
    db/ session.py  models.py  migrations/
    schemas/ vapi.py  orders.py  reservations.py  calls.py  menu.py
    routers/ health.py ✅  vapi.py  orders.py  reservations.py  calls.py  menu.py
    services/ menu_service  order_service  reservation_service  call_service  transfer_service  tool_registry
  seed/ menu.py
  tests/ test_health.py ✅
  Dockerfile ✅  .env.example ✅  pyproject.toml ✅
```

## Modelo de datos
Tablas: `menu_items`, `orders`, `order_items`, `reservations`, `calls`, `transfers`.

Reglas de diseño (corrigen errores de los documentos originales):
- `orders.number`: **`Identity()` o `Sequence`**, no `autoincrement=True` (solo funciona en PK).
- `idempotency_key` **unique** en `orders` y en `reservations`; insertar y capturar `IntegrityError` (no "buscar y luego insertar").
- `session_id` (string; el header `X-Session-Id` del visitante) en `calls`, `orders`, `reservations`, `transfers` para aislar datos por visitante.
- `calls` única por (`provider`, `provider_call_id`) → el webhook hace upsert (los proveedores reenvían).
- `menu_items`: id, nombre, categoría, precio `Numeric(10,2)`, alérgenos, `available`.
- `orders.status`: enum `confirmed → preparing → ready`; validar transiciones.
- Zona horaria y moneda en `Settings` (no fijas en el código).

## Endpoints

**Agente (autenticados por proveedor; ambos siempre montados)**

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/vapi/tools` | tool calls de Vapi (secreto Bearer / X-Vapi-Secret) |
| POST | `/retell/tools` | custom function de Retell (firma `X-Retell-Signature`) |
| GET | `/voice/config` | proveedor activo |
| POST | `/voice/web-call` | datos para iniciar la llamada web con el proveedor activo |
| POST | `/vapi/webhook` · `/retell/webhook` | fin de llamada (fase 5) |

**Panel** (con `response_model`, paginación `limit/offset` y `?since=` para polling eficiente; filtrados por header `X-Session-Id`)

| Método | Ruta |
|---|---|
| GET | `/orders` · PATCH `/orders/{id}/status` |
| GET | `/reservations` |
| GET | `/calls` · `/calls/{id}` |
| GET | `/menu` |
| GET | `/health` |

Opcional: `GET /events` (SSE) para empujar "pedido creado" al panel en vez de polling.

## Router de tools (ver `docs/08`, fase 2: multi-proveedor)
- Un endpoint, un registro `TOOLS = {nombre: función}`.
- Tipar el payload con modelos Pydantic (`schemas/vapi.py`), no `dict`.
- `arguments` puede llegar como **string JSON** según el formato → `json.loads` si es `str`.
- Un `rollback` por tool call fallida; una sesión/transacción por tool call, no una compartida en el bucle.
- Siempre responder 200 con `{"results":[{"toolCallId","result"}]}`; `result` en una sola línea. Verificar formato vigente en docs de Vapi.
- `BusinessError` → mensaje corto para Sofía; cualquier otra excepción → "Hubo un problema técnico. Ofrece pasar con una persona." (y log con `call_id`).

## Las 4 tools
Respuestas cortas, aptas para voz; montos formateados para hablar (moneda desde `Settings`).

- **`get_menu`** (`category?`, `query?`): platos con nombre, precio y alérgenos relevantes, en una frase. Devuelve ids internos que el agente reutiliza.
- **`create_order`** (`customer_name`, `type` pickup|delivery, `address?`, `items[{name|id, quantity, options?, notes?}]`, `notes?`):
  - solo tras confirmación explícita; delivery exige dirección;
  - validar existencia y disponibilidad (plato agotado → `BusinessError`);
  - coincidencia por id o aproximada; si hay ambigüedad → error pidiendo aclarar;
  - **total calculado en backend**; idempotencia por `tool_call_id`;
  - devuelve número de pedido, total y tiempo estimado.
- **`create_reservation`** (`customer_name`, `party_size`, `date`, `time`, `notes?`): horario de atención, máximo de personas, fecha futura (en la zona horaria configurada); si no es válida, proponer alternativa. Idempotente.
- **`transfer_to_human`** (`reason`): registra en `transfers`; simulado en el demo (Vapi permite transferencia real a un número).

## Webhook de fin de llamada
`end-of-call-report` → upsert en `calls` (id de Vapi, duración, transcripción, resumen), `outcome` **derivado** de pedidos/reservas/transferencias enlazados por `call_id` (no del LLM): pedido | reserva | info | transferida | abandonada. Si el procesamiento es pesado, `BackgroundTasks` con **su propia sesión** (la de la petición ya estará cerrada).

## Fecha y hora
Inyectar la fecha actual en el prompt (variable `{{now}}` de Vapi) para que "mañana a las 8" se resuelva bien; `timezone` en `Settings` (p. ej. `America/La_Paz`).

## Despliegue
- Dockerfile con `uv sync --frozen`, usuario no root y `$PORT` (ya creado).
- Migraciones: `alembic upgrade head` como paso de release (o al arranque), no dentro de cada petición.
- Neon: `ssl=require`; autosuspend añade latencia al primer request → mantener caliente (ping a `/health` desde el frontend al cargar + monitor externo).
- Objetivo: tools < 1 s en condiciones normales.

## Tests mínimos
1. `create_order` válido: crea pedido y calcula total.
2. Plato agotado: mensaje de error, sin pedido.
3. Mismo `tool_call_id` dos veces (también en concurrencia): no duplica.
4. `arguments` como string JSON y como objeto.
5. Reserva fuera de horario / 20 personas: rechaza con alternativa.
6. Sin secreto: 401.
7. Webhook: guarda transcripción y resumen; reenvío no duplica.
8. Integración: payload real de Vapi grabado contra Postgres de prueba (testcontainers o rama de Neon).
