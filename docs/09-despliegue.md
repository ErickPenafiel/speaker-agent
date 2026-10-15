# 9. Despliegue y operación

> **Qué está verificado y qué no.** Verificado en local: imagen Docker (build, arranque desde una base vacía con migraciones y seed, `healthcheck`, usuario no root, logs JSON), conexión a través de un pgbouncer real, los comandos de CI. **No verificado** (no hay cuentas): despliegue real en Fly/Render, ejecución de los workflows en GitHub, y la configuración en los dashboards de Vapi/Retell. Esos pasos están escritos a partir de la documentación y conviene revisarlos al hacerlos.

## 1. Variables de entorno

| Variable | Para qué | Notas |
|---|---|---|
| `DATABASE_URL` | Base de datos de la app | Pega la URL de Neon tal cual; se convierte sola (`+asyncpg`, `sslmode`→`ssl`, sin `channel_binding`) |
| `DATABASE_URL_DIRECT` | Migraciones | URL **sin** `-pooler`. Si está vacía, migra por `DATABASE_URL` |
| `DB_POOLED` | Forzar modo pooler | Vacío = autodetecta el host `-pooler` |
| `FRONTEND_ORIGIN` | CORS | URL exacta del frontend (las previews de Vercel tienen otra URL) |
| `VOICE_PROVIDER` | Proveedor activo | `vapi` \| `retell` |
| `VAPI_WEBHOOK_SECRET`, `VAPI_PUBLIC_KEY`, `VAPI_ASSISTANT_ID` | Vapi | La clave pública es pública; el secreto no |
| `RETELL_API_KEY`, `RETELL_AGENT_ID` | Retell | La API key solo vive en el backend; también verifica las firmas |
| `ENVIRONMENT`, `LOG_LEVEL`, `LOG_FORMAT` | Logs | Producción: `production` y `json` (la imagen ya trae `LOG_FORMAT=json`) |
| `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `RELEASE` | Sentry | Sin DSN queda apagado |
| `RATE_LIMIT_*`, `WEB_CALL_DAILY_CAP` | Límites | Ver `docs/08`, fase 6 |
| `DATA_RETENTION_DAYS`, `CLEANUP_INTERVAL_HOURS` | Limpieza | 7 días / cada 6 h; 0 desactiva la tarea interna |
| `RUN_MIGRATIONS=1`, `SEED_ON_START=1` | Arranque del contenedor | Opcionales, ver `scripts/start.sh` |
| `CAPTURE_PAYLOADS_DIR` | Solo desarrollo | Ver sección 6 |

## 2. Neon

1. Crear el proyecto y copiar **dos** cadenas de conexión: la *pooled* (host con `-pooler`) y la *direct*.
2. `DATABASE_URL` = pooled; `DATABASE_URL_DIRECT` = direct. Pegarlas tal cual (con `sslmode=require&channel_binding=require`).
3. El endpoint pooled usa pgbouncer en modo transacción. La app desactiva ahí la caché de sentencias preparadas (`statement_cache_size=0` y `prepared_statement_cache_size=0`).
   - **Verificado con un pgbouncer 1.26 real**: con pgbouncer sin soporte de sentencias preparadas (versiones antiguas), sin esa configuración fallan 30 de 30 tareas con `prepared statement ... does not exist`; con ella funcionan 30 de 30. Con un pgbouncer moderno funcionan ambas. Es decir: es necesaria en pgbouncers antiguos y inocua en los modernos.
4. Neon se suspende tras un rato sin uso; la primera conexión tarda más. El engine usa `timeout=15`, `pool_pre_ping` y `pool_recycle=300`.

## 3. Despliegue del backend

**Restricción importante: una sola instancia y un solo proceso.** El rate limit y el tope diario viven en memoria; con varias instancias cada una tiene sus contadores y el límite efectivo se multiplica. Tampoco ejecutar `RUN_MIGRATIONS=1` en varias instancias a la vez (Alembic no bloquea).

### Fly.io (`agent-backend/fly.toml`)
```bash
cd backend
fly launch --no-deploy --copy-config --dockerfile Dockerfile
fly secrets set DATABASE_URL='...' DATABASE_URL_DIRECT='...' FRONTEND_ORIGIN='https://...' \
  VAPI_WEBHOOK_SECRET='...' VAPI_PUBLIC_KEY='...' VAPI_ASSISTANT_ID='...' SENTRY_DSN='...'
fly deploy
```
Migraciones: `release_command = "alembic upgrade head"`. `min_machines_running = 1` evita el cold start (recomendado para la demo; revisar el coste vigente).

### Render (`render.yaml`)
Blueprint con plan gratuito, que **duerme el servicio**: usar el workflow de la sección 5. Sin `preDeployCommand` en el plan gratuito, las migraciones van en el arranque (`RUN_MIGRATIONS=1`).

### Qué hace el contenedor
`scripts/start.sh` → (opcional) `alembic upgrade head` → (opcional) `python -m seed.demo` (menú + datos de ejemplo; también refresca las fechas de las reservas de ejemplo) → `uvicorn --proxy-headers --forwarded-allow-ips='*' --no-access-log`. `HEALTHCHECK` consulta `/health`. Corre como usuario `app`.

> `--forwarded-allow-ips='*'` es correcto detrás del proxy de la plataforma. Si se expone uvicorn directamente a internet, quitarlo (permitiría falsear la IP y evadir el rate limit).

## 4. Configurar Vapi / Retell (a mano en sus dashboards)

URL base: la pública del backend (`https://<tu-api>`). Nombres de campos: **verificar en la documentación vigente.**

| | Vapi | Retell |
|---|---|---|
| Tools | URL `…/vapi/tools` en cada tool | URL `…/retell/tools` en cada *custom function* |
| Fin de llamada | Server URL `…/vapi/webhook` (mensaje `end-of-call-report`) | Webhook `…/retell/webhook` (`call_ended`, `call_analyzed`) |
| Autenticación | Credencial con `Authorization: Bearer <secreto>` o header `X-Vapi-Secret`; el mismo valor que `VAPI_WEBHOOK_SECRET` | Firma `X-Retell-Signature` con la API key (`RETELL_API_KEY`) |
| Esquemas de las tools | `uv run python -m scripts.print_tool_schemas` | ídem |
| Cortes de llamada | `maxDurationSeconds`, `silenceTimeoutSeconds` | duración máxima del agente |
| Variables del prompt | `{{now}}` (fecha actual) | `retell_llm_dynamic_variables.now` (la fija `/voice/web-call`) |

Además, **en el dashboard**: límite de gasto de la cuenta y, en Vapi, restringir los dominios permitidos de la clave pública. Esto no se puede hacer desde el código y es la defensa principal contra el gasto de crédito.

Retell no envía un id por invocación de la tool: la idempotencia se calcula con `call_id` + argumentos (dos pedidos idénticos en la misma llamada se tratan como uno).

## 5. Calentamiento

| Endpoint | Toca la BD | Uso |
|---|---|---|
| `GET /health` | no | liveness (healthcheck de la plataforma) |
| `GET /health/ready` | sí (`SELECT 1`) | despierta el servicio **y** Neon; 503 si la BD no responde |

- El frontend debe llamar a `/health/ready` al cargar la página (con reintentos) antes de habilitar el botón de llamar.
- `.github/workflows/keepwarm.yml` hace ping a `/health/ready` cada 10 min; definir la variable de repositorio `API_URL`. El cron de Actions puede retrasarse varios minutos: es un apoyo, no una garantía. Alternativa: un monitor externo (UptimeRobot, cron-job.org).
- Con Fly y `min_machines_running = 1` el cold start del servicio desaparece, pero Neon sigue pudiendo suspenderse: el ping a `/ready` lo cubre.

## 6. Observabilidad

**Logs** (JSON en producción, `structlog` + `logging` + uvicorn por un único handler). Eventos: `request` (método, ruta sin query, estado, `duration_ms`, `request_id`), `tool_call` (herramienta, `outcome`: `ok`/`business_error`/`unknown_tool`/`tech_error`, `duration_ms`, `slow`, `call_id`), `call_report_saved`, `tool_failed`, `readiness_failed`, `cleanup_done`. Las tools que tardan más de 1 s salen como *warning* con `slow=true` (criterio de aceptación del proyecto). Cada respuesta lleva `X-Request-Id`, generado por el servidor.

**Regla de privacidad**: no se registran argumentos ni respuestas de las tools, transcripciones, resúmenes, nombres, direcciones, headers (el `X-Session-Id` es una credencial) ni query strings. Tests lo comprueban. Por eso se desactiva el access log de uvicorn (incluye la query string) dentro de `configure_logging`, aunque no se pase `--no-access-log`.

**Sentry** (opcional): `send_default_pii=False`, sin cuerpos de petición, y `before_send` que elimina headers, datos, cookies, query string y usuario, y reemplaza el texto de los errores de base de datos (Postgres adjunta la fila en `DETAIL`). Los mensajes de otras excepciones sí se envían: no incluir datos de clientes en mensajes de error. El engine usa `hide_parameters=True` (los errores no llevan `[parameters: ...]`).

**Captura de payloads reales** (cierra lo "pendiente de verificar en vivo"):
1. En desarrollo, con el túnel público activo: `CAPTURE_PAYLOADS_DIR=/ruta/fuera/del/repo`.
2. Hacer una llamada real de cada proveedor que cree un pedido, una reserva y una transferencia.
3. Se guardan, ya autenticadas, los cuerpos de `/vapi/*` y `/retell/*` (sin secretos ni firmas). **Contienen datos personales**: anonimizar antes de copiarlos a `agent-backend/tests/fixtures/`.
4. Comparar con los fixtures actuales (reproducen la *forma documentada*, no son capturas) y ajustar el parser que difiera. Puntos a mirar: dónde llegan resumen y duración en Vapi, si `call.metadata.sessionId` llega en ambos, y el formato de `toolCallList`.

## 7. Limpieza programada
La tarea interna corre al arrancar y cada 6 h. En servicios que se duermen no corre mientras duermen: añadir un cron externo `uv run python -m app.jobs.cleanup` (o la pasada equivalente en el contenedor).

## 8. Lista de comprobación antes de una demo
- [ ] `curl https://<api>/health/ready` → `{"status":"ok","db":"ok"}`
- [ ] `VOICE_PROVIDER` correcto y claves del proveedor cargadas (`POST /voice/web-call` responde 200)
- [ ] Tools y webhook apuntan a la URL pública vigente (el túnel de desarrollo cambia)
- [ ] Una llamada de prueba: pedido visible en el panel y llamada con resumen
- [ ] Límite de gasto y duración máxima configurados en el proveedor
- [ ] `FRONTEND_ORIGIN` coincide con la URL del frontend desplegado
- [ ] Datos de ejemplo recientes (`SEED_ON_START=1` o `python -m seed.demo`)
