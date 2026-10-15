# 5. Seguridad, privacidad y costos

La demo es **pública**: cualquiera puede llamar al agente y ver el panel.

## Costos (Vapi)
La clave **pública** va en el frontend, así que cualquiera puede gastar tu crédito.
- Restringir **dominios permitidos** de la clave pública en el dashboard de Vapi.
- Fijar un **límite de gasto** en la cuenta.
- En el asistente: `maxDurationSeconds` (p. ej. 180) y `silenceTimeoutSeconds`.
- Opcional: captcha (Cloudflare Turnstile) antes de habilitar la llamada.

## Privacidad
Los visitantes hablan con su voz real y verían las transcripciones de otros.
- Generar un `sessionId` en el navegador, enviarlo en `metadata` al iniciar la llamada, guardarlo en `calls/orders/reservations` y filtrar el panel con el header `X-Session-Id`.
- Mostrar datos de ejemplo sembrados cuando la sesión no tenga datos propios.
- Job de limpieza que borre datos de más de N días.
- Logs sin datos sensibles; datos del demo siempre ficticios.

## API
- Secreto verificado en cada petición de Vapi (`hmac.compare_digest`); sin secreto → 401.
- `PATCH /orders/{id}/status` es público: enum + transiciones válidas + rate limit (slowapi **conectado**: `Limiter`, handler y middleware).
- CORS con `frontend_origin` explícito (considerar las URLs de preview de Vercel).
- Validar todo con Pydantic; si falla, devolver mensaje corto para el agente.
- Claves privadas solo en variables de entorno del backend; nunca en el repo ni en el frontend.

## Multi-proveedor
- **Retell**: la API key vive solo en el backend; el navegador recibe un `access_token` de un solo uso creado por `POST /voice/web-call`. Ese endpoint **cuesta dinero** (cada llamada consume crédito) → rate limit por IP y por `session_id` (fase 6), `max_call_duration` en el agente y límite de gasto en la cuenta.
- **Vapi**: la clave pública es pública por diseño; restringir dominios y fijar límite de gasto en el dashboard.
- Las firmas de Retell se verifican sobre el **cuerpo crudo** con ventana de 5 min; sin `RETELL_API_KEY` configurada toda petición se rechaza (401).
- Las rutas del proveedor inactivo siguen montadas pero rechazan lo que no venga firmado/autenticado.

## Estado de implementación (fase 6)
- Aislamiento por `X-Session-Id` en todo el panel; el `PATCH` ya no permite tocar pedidos ajenos. Ver `docs/08`.
- Rate limit por IP + tope diario global de `web-call` + `Retry-After` en 429.
- Datos de ejemplo de solo lectura (sesión `demo`, no reclamable) y limpieza automática con retención de 7 días.
- Fase 7: logs y Sentry sin datos de clientes, `hide_parameters` en SQL, `X-Request-Id` generado por el servidor. Detalle en `docs/09`.
- Sigue siendo manual: fijar límites de gasto y duración en el dashboard del proveedor (no se puede hacer desde el código).
