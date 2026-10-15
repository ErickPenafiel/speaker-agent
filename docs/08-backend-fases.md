# 8. Backend: plan por fases

Cada fase termina con algo que se puede **ejecutar y probar**. No se pasa a la siguiente sin tests en verde (`uv run pytest -q`, `uv run ruff check .`).

| Fase | Entregable | Estado |
|---|---|---|
| 0 | Esqueleto: `/health`, config, secreto, Dockerfile | ✅ |
| 1 | Datos: Postgres local (docker), modelos, Alembic, seed del menú, `GET /menu` | ✅ |
| 2 | Capa de voz multi-proveedor (Vapi **o** Retell): `tool_runner` común, `/vapi/tools`, `/retell/tools`, `/voice/web-call`, `get_menu` | ✅ |
| 3 | Pedidos: `create_order` (validación, total, idempotencia) + `GET/PATCH /orders` | ✅ |
| 4 | Reservas y transferencia: `create_reservation`, `transfer_to_human`, `GET /reservations` | ✅ |
| 5 | Webhook y llamadas (Vapi y Retell): reporte normalizado, upsert, `outcome` derivado, `GET /calls` y detalle | ✅ |
| 6 | Panel público seguro: aislamiento por `X-Session-Id`, datos de ejemplo, rate limit, tope diario de llamadas, limpieza | ✅ |
| 7 | Robustez y despliegue: logs estructurados sin datos personales, Sentry depurado, Neon/pooler, readiness, flujo completo por proveedor, contenedor, Fly/Render/CI | ✅ |

## Fase 1 — Datos (hecha)
- `docker-compose.yml` con Postgres 17 (`speaker_agent` y `speaker_agent_test`).
- `app/db/session.py` (engine async, `get_session`), `app/db/models.py` (6 tablas), migración inicial con Alembic.
- Seed idempotente del menú ficticio (con 2 platos agotados).
- `GET /menu` y `menu_service.get_menu_tool` (texto corto para voz).
- Tests: menú sembrado, filtro por categoría, plato agotado marcado.
- **Criterio de salida**: `alembic upgrade head` + `python -m seed.menu` + `GET /menu` devuelve datos.

## Fase 2 — Capa de voz multi-proveedor (hecha)
**Requisito añadido:** poder cambiar entre **Vapi** y **Retell** sin tocar la lógica de negocio.

Diseño:
- Las rutas de **ambos** proveedores están siempre montadas: `/vapi/*` y `/retell/*`, cada una con su propia autenticación y parser. Ambas delegan en `services/tool_runner.py` (una transacción por tool call, commit/rollback, nunca lanza, resultado en una línea).
- El proveedor **activo para el frontend** se elige con `VOICE_PROVIDER=vapi|retell`. Cambiarlo = cambiar una variable de entorno + apuntar la URL de las tools en el dashboard del otro proveedor.
- `app/providers/`: `VoiceProvider` (Protocol) con `create_web_call(session_id, language, now) -> WebCallInfo`.
  - **Vapi**: devuelve clave pública + id de asistente + metadata (la clave pública es pública por diseño).
  - **Retell**: el servidor llama a `POST /v3/create-web-call` con la API key (que nunca sale del backend) y devuelve el `access_token`.
- `GET /voice/config` → `{provider}`; `POST /voice/web-call {session_id, language}` → `WebCallInfo` (503 si faltan credenciales, 502 si el proveedor falla).

Diferencias verificadas en la documentación (oct 2026):

| | Vapi | Retell |
|---|---|---|
| Petición de tool | `message.type="tool-calls"`, `toolCallList[]` (`function.{name,arguments}` o plano; `arguments` objeto o string) | `{name, args, call:{call_id, metadata,…}}`, una función por petición |
| Respuesta | `{"results":[{"toolCallId","result"}]}`, string plano de una línea, siempre 200 | string/JSON (máx. 15 000 caracteres), 2xx |
| Id por invocación | `toolCall.id` (sirve para idempotencia) | **no hay**: idempotencia por `call_id` + nombre + args |
| Autenticación | credencial en el dashboard: `Authorization: Bearer` o `X-Vapi-Secret` (ambos aceptados) | `X-Retell-Signature: v=<ms>,d=<hex>` = HMAC-SHA256(api_key, cuerpo_crudo + ms), ventana 5 min |
| Llamada web | SDK con clave pública + assistantId | token creado en servidor (`/v3/create-web-call`) |
| Webhook de fin | `end-of-call-report` | `call_ended` / `call_analyzed` (reintenta 3 veces; idempotencia por `event + call_id`) |

Tests: 24 en total (secreto 401, ambos estilos de auth, `arguments` objeto/string, forma plana/anidada, herramienta desconocida, errores de negocio/inesperados, firma Retell válida/alterada/expirada/sin clave, creación de llamada Retell con transporte simulado, 502/503, validación de entrada).

**Pendiente de verificar en vivo** (no se puede desde aquí): que `metadata.sessionId` llegue en `call.metadata` en Vapi al iniciar con el SDK web; el ID de la tool call en Retell si algún día lo añaden.

## Fase 3 — Pedidos (hecha)
`create_order` (tool) y panel de pedidos. Reglas implementadas:
- **Confirmación explícita**: la tool exige `customer_confirmed=true`; si no, devuelve "resume el pedido y pide confirmación". Es una red de seguridad además del prompt.
- **Total en el backend**: suma `precio × cantidad` desde la base; el LLM no puede aportar precios ni total (un `total` extra en los argumentos se ignora).
- **Platos**: por `id` (de `get_menu`) o por nombre — exacto, parcial (sin acentos ni mayúsculas) o con errata leve. Ambiguo → "Hay varias opciones…, pregunta cuál"; inexistente → "No encontré X"; agotado → "X está agotado". Un error en cualquier línea no crea nada.
- **Tipo**: `pickup`/`delivery` con sinónimos en español (`recoger`, `a domicilio`…); delivery exige dirección. Cantidades como string (`"2"`) se aceptan.
- **Idempotencia**: clave = hash de `tool_call_id` (Vapi) o de `call_id + argumentos canónicos` (Retell, que no envía id). Se detecta antes de insertar y, para carreras, con savepoint + `IntegrityError` sobre la restricción `unique`. Test con 4 peticiones simultáneas → 1 pedido.
- **Respuesta para voz**: "Pedido 12 confirmado. Total 108 BOB. Estará listo en unos 20 minutos." (20 min recoger / 40 delivery, configurables). Dinero con `format_money` (sin decimales si es entero; corrige el redondeo de 12.50 → "12" de la fase 1).

Panel:
- `GET /orders?limit&offset&since` (más nuevos primero, con líneas).
- `PATCH /orders/{id}/status`: `confirmed → preparing → ready`; mismo estado = idempotente; salto o retroceso → 409; estado inválido → 422; no existe → 404.
- El filtrado por visitante (`X-Session-Id`) llega en la fase 6; hoy el listado es global.

Configuración de la tool en los proveedores: `uv run python -m scripts.print_tool_schemas` imprime el JSON Schema de `get_menu` y `create_order` para pegarlo en Vapi o Retell.

Tests: 38 en total (14 nuevos de pedidos).

## Fase 4 — Reservas y transferencia (hecha)
**`create_reservation`** (`customer_name`, `party_size`, `date` YYYY-MM-DD, `time` HH:MM, `notes?`). Todas las reglas usan la hora local del restaurante (`TIMEZONE`) y son configurables:

| Regla | Config | Respuesta del agente |
|---|---|---|
| Máximo de personas | `MAX_PARTY_SIZE=12` | "Para más de 12 personas no puedo reservar por aquí. Ofrece pasar con una persona." |
| Horario | `RESTAURANT_OPEN/CLOSE` (12:00–23:00); última reserva = cierre − 60 min | "Atendemos de 12:00 a 23:00; la última reserva es a las 22:00. ¿Le sirve mañana a las 12:00?" |
| Margen mínimo | 30 min desde ahora | "Esa hora ya pasó o es muy pronto. ¿Le sirve hoy a las 15:30?" |
| Anticipación máxima | 60 días | "Solo reservamos hasta 60 días por adelantado…" |

- **Alternativa propuesta**: hora válida más cercana el mismo día; si hoy ya no queda margen, el siguiente horario libre (hoy redondeado a 30 min, o mañana a la apertura).
- **Formatos de hora**: `20:00`, `20:00:00`, `8:00 PM`, `8pm`. Una hora suelta (`8`) se rechaza por ambigua.
- **Respuesta hablada**: "Reserva confirmada para 4 personas mañana a las 20:00 a nombre de Ana Pérez." (hoy / mañana / "el viernes 16 de octubre").
- **Idempotencia**: igual que en pedidos (tool_call_id o call_id+args). Un reintento tardío devuelve la reserva existente aunque el horario ya haya pasado.

**`transfer_to_human`** (`reason?`): registra en `transfers` (con clave idempotente) y responde al agente que despida al cliente porque lo comunica con una persona. Simulado; la transferencia real a un número se configura en el proveedor.

**Panel**: `GET /reservations?limit&offset&since&date_from&date_to`, ordenado por fecha y hora.

**Refactor**: `services/idempotency.py` (`idempotency_key`, `insert_once` con savepoint) compartido por pedidos, reservas y transferencias. Migración `806a912c0919` (clave idempotente en `transfers`), verificada subida/bajada y `alembic check`.

Tests: 69 en total (31 nuevos). La hora se inyecta (`reservation_service._now`) y se fija en jueves 2026-10-08 15:00, así que no dependen del día en que corran.

Limitación conocida: no hay control de capacidad ni de mesas (fuera del alcance del demo); dos reservas a la misma hora siempre se aceptan.

## Fase 5 — Webhook y llamadas (hecha)
**Endpoints de entrada**: `POST /vapi/webhook` (secreto) y `POST /retell/webhook` (firma). Siempre responden 200 `{"ok": true}`; solo guardan `end-of-call-report` (Vapi) y `call_ended` / `call_analyzed` (Retell). Los demás eventos se ignoran.

**Reporte normalizado** (`CallReport`): `provider`, `provider_call_id`, `session_id`, `started_at`, `duration_seconds`, `transcript` (`[{role: user|assistant, text}]`), `summary`. Cada proveedor tiene su parser (`parse_end_of_call`, `parse_call_event`); el resto del sistema no sabe de Vapi ni Retell.
- **Vapi**: transcripción de `artifact.messages` (`message`/`content`; se descartan `system`, `tool` y vacíos; `bot` → assistant). El resumen se busca en `analysis.summary`, `summary` y `artifact`; la duración en `durationSeconds` o `endedAt − startedAt`. *La doc consultada no fija del todo dónde van resumen y duración, por eso el parser es tolerante.*
- **Retell**: `transcript_object` (`agent` → assistant; `transfer_target` se descarta), tiempos de `start/end_timestamp` o `duration_ms`, resumen de `call_analysis.call_summary`. `call_ended` no trae `call_analysis`; llega después en `call_analyzed`.

**Guardado** (`call_service.save_report`):
- Upsert atómico por (`provider`, `provider_call_id`) con `ON CONFLICT DO UPDATE` y `COALESCE`: un campo ausente **no pisa** lo guardado, así `call_ended` y `call_analyzed` se fusionan en cualquier orden y los reintentos no duplican (5 peticiones simultáneas → 1 fila).
- `transcript` usa `JSONB(none_as_null=True)`: sin ello, `None` se guardaba como JSON `null` y pisaba la transcripción al fusionar.
- **`outcome` derivado de lo realmente guardado** (pedidos, reservas y transferencias con ese `call_id`), no del LLM. Prioridad: `order` > `reservation` > `transferred` > `info`; sin ningún turno del cliente → `abandoned`.
- `session_id`: el de la metadata de la llamada; si no viene, el del primer pedido/reserva/transferencia enlazado.

**Panel**
- `GET /calls?limit&offset&outcome&since` (más recientes primero, sin transcripción).
- `GET /calls/{id}`: transcripción completa + pedidos, reservas y transferencias de esa llamada.

**Migración** `b1f0c5a7d2e4`: `vapi_call_id` → `provider_call_id`, nueva columna `provider`, unicidad por (provider, id). Verificada subida/bajada y `alembic check`.

Tests: 98 en total (29 nuevos): parsers con payloads de ambos proveedores, fusión en cualquier orden, no sobrescritura con nulos, concurrencia, firma de Retell, panel y un flujo completo (tool → webhook → llamada enlazada al pedido).

**Pendiente de verificar en vivo**: la forma exacta de `end-of-call-report` en Vapi (resumen, duración) y que `call.metadata.sessionId` llegue en ambos proveedores. Si algo difiere, solo cambia el parser correspondiente.

## Fase 6 — Panel público seguro (hecha)
**Aislamiento por visitante**
- Todo el panel (`/orders`, `/reservations`, `/calls`, `/calls/{id}`, `PATCH /orders/{id}/status`) exige el header `X-Session-Id` (16–64 caracteres `[A-Za-z0-9_-]`; si falta o es inválido → 422). `/menu` y `/health` no lo necesitan.
- El id **es la credencial del visitante**: el frontend debe generarlo con `crypto.randomUUID()` y guardarlo en `localStorage`. Nunca se devuelve en las respuestas.
- Cada consulta filtra por esa sesión. Pedidos o llamadas de otro visitante → **404** (también en el `PATCH`, que antes permitía modificar los de cualquiera). Filas sin sesión no las ve nadie.
- `session_id` llega a los registros desde la metadata de la llamada (`/voice/web-call` la fija) o, en las llamadas, desde los pedidos/reservas enlazados.

**Datos de ejemplo** (`uv run python -m seed.demo`, idempotente)
- Sesión reservada `demo` (4 caracteres: ningún cliente puede reclamarla, el header exige ≥16). 2 pedidos (uno `ready`, uno `preparing`), 2 reservas, 6 llamadas con transcripción y todos los `outcome` (order ×2, reservation, info, transferred, abandoned), una transferencia.
- Si el visitante **no tiene ninguna fila** de ese tipo, ve las de ejemplo; en cuanto crea la primera, solo ve las suyas (por entidad). Todas las respuestas incluyen `is_demo` para que la UI ponga la etiqueta "Ejemplo".
- Son **de solo lectura**: `PATCH` sobre un pedido de ejemplo → 403. Las llamadas de ejemplo se pueden abrir (son públicas).
- Las fechas de las reservas son relativas al día en que se ejecuta el seed; repetirlo de vez en cuando.

**Rate limit** (`slowapi`, por IP, configurable en `.env`; 429 con `Retry-After`)
| Ruta | Límite por defecto |
|---|---|
| lecturas del panel | `120/minute` |
| `PATCH` de estado | `30/minute` |
| `POST /voice/web-call` | `5/minute;30/hour` |
| tools y webhooks | sin límite (tráfico autenticado del proveedor) |

- **Tope diario global** de `web-call` (`WEB_CALL_DAILY_CAP=200`, en memoria, 0 = sin tope): válvula de seguridad contra el gasto de crédito aunque cambien de IP. Se reinicia con el proceso.
- Detrás de un proxy el `Dockerfile` arranca uvicorn con `--proxy-headers` para ver la IP real del cliente. **Si se despliega en otro sitio sin proxy de confianza, quitar `--forwarded-allow-ips=*`** (permitiría falsear la IP).

**Limpieza**: `app/jobs/cleanup.py` borra pedidos, reservas, transferencias y llamadas con más de `DATA_RETENTION_DAYS` (7) — incluidas las filas sin sesión — y nunca la sesión `demo`. Corre al arrancar y cada `CLEANUP_INTERVAL_HOURS` (6) como tarea de fondo (0 la desactiva), y también como una pasada suelta: `uv run python -m app.jobs.cleanup` (cron externo; recomendable en servicios gratuitos que se duermen).

**Decisión: sin SSE.** El polling con `?since=` basta para el panel y un broadcaster en memoria falla con más de una instancia. Se retoma solo si la UI lo necesita.

**Verificado**: 124 tests (26 nuevos), servidor real contra la base de desarrollo (422 sin header, ejemplo para un visitante nuevo, 403 al modificar un ejemplo, OpenAPI con `is_demo`) y el `Dockerfile` construido y ejecutado (arranca con `$PORT`, usuario no root, `/health` y `/menu` OK).

**Cambios que afectan al frontend**: enviar `X-Session-Id` en todas las llamadas del panel y el mismo id en `POST /voice/web-call`; mostrar la etiqueta "Ejemplo" según `is_demo`; manejar 429 (mostrar `Retry-After`) y 403.

## Fase 7 — Robustez y despliegue (hecha)
Detalle operativo y comandos en `docs/09-despliegue.md`. Resumen de lo construido y de cómo se verificó:

**Logs estructurados** (`app/core/logging.py`): un único pipeline para structlog, `logging` y uvicorn; JSON en producción. Middleware que asigna `request_id` (generado en el servidor, nunca el del cliente), lo devuelve en `X-Request-Id` y registra método, ruta, estado y duración. Cada tool deja un `tool_call` con `outcome` y `duration_ms` (*warning* si pasa de 1 s); cada reporte, un `call_report_saved`. **Nada de datos de clientes, headers ni query strings**, con tests que lo comprueban.
> Hallazgo al verificar con un servidor real: el access log de uvicorn escribía la query string y mi configuración anulaba el `--no-access-log`. Ahora se desactiva dentro de `configure_logging`.

**Sentry** (opcional, solo con DSN): sin PII, sin cuerpos, y `before_send` que elimina headers/datos/cookies/query/usuario y el texto de los errores de base de datos (Postgres adjunta la fila en `DETAIL`). `hide_parameters=True` en el engine.

**Neon**: la URL se pega tal cual (`postgresql://…?sslmode=require&channel_binding=require` → asyncpg). Endpoint pooled autodetectado (`-pooler`, o `DB_POOLED`) con las cachés de sentencias preparadas desactivadas; `DATABASE_URL_DIRECT` para migraciones. **Verificado con un pgbouncer 1.26 real**: en un pgbouncer sin soporte de sentencias preparadas, sin la configuración fallan 30/30 tareas y con ella 30/30 funcionan; en uno moderno funcionan ambas.

**Salud**: `/health` (liveness, sin BD) y `/health/ready` (`SELECT 1`; despierta Neon; 503 sin filtrar detalles).

**Flujos completos con payloads de proveedor** (`tests/fixtures`, `tests/test_integration_flow.py`): una llamada entera por proveedor (3 tools → reintento del proveedor → reporte final repetido → panel). Cubre que Vapi envía las tools en dos formatos a la vez y cada una se ejecuta una sola vez, y que `call_analyzed` de Retell puede llegar antes que `call_ended`. **Los fixtures reproducen la forma documentada, no son capturas reales** (no hay cuentas). Para cerrar esa brecha: `CAPTURE_PAYLOADS_DIR` (solo desarrollo) guarda los payloads autenticados de una llamada real para convertirlos en fixtures.

**Contenedor**: `scripts/start.sh` (migraciones y seed opcionales), `HEALTHCHECK`, usuario no root, `--proxy-headers`. Probado: build, arranque desde una base vacía (migra, siembra, queda `healthy`, `/health/ready` OK, datos de ejemplo visibles).

**Despliegue y CI**: `agent-backend/fly.toml`, `render.yaml`, `.github/workflows/ci.yml` (ruff, formato y pytest con Postgres de servicio + build del frontend) y `keepwarm.yml`. Sintaxis validada y los comandos de CI ejecutados en local; **no ejecutados en GitHub/Fly/Render**.

**Tests**: 163 en total (39 nuevos).

**Límites conocidos**: rate limit y tope diario en memoria (una sola instancia); sin Redis; sin métricas ni trazas (Sentry con `traces_sample_rate=0`); la configuración de los dashboards de Vapi/Retell y sus límites de gasto es manual.
