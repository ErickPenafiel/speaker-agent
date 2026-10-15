# 6. Plan, criterios y video

## Plan por días

| Día | Backend | Frontend |
|---|---|---|
| 0 ✅ | Esqueleto FastAPI (`/health`, config, seguridad, Dockerfile, test) | Esqueleto Vite + Tailwind v4 + dependencias |
| 1 | Neon, modelos, Alembic, seed del menú, `get_menu`, túnel público; asistente Vapi con prompt y llamada web | Cliente API tipado + MSW, pantalla de llamada: orbe, transcripción, SDK |
| 2 | `create_order` (validación, total, idempotencia), `create_reservation`, `transfer_to_human`, webhook, secreto | Pedidos (kanban), reservas, llamadas con datos reales, refetch, errores y backend dormido, panel en vivo |
| 3 | Endpoints del panel con filtro por sesión, tests, 12 guiones de prueba, ajustes de prompt, deploy, README | Responsive, detalle de llamada, selector EN/ES, deploy Vercel, capturas, GIF y video |

Menú (pantalla E) es lo primero que se recorta si falta tiempo.

## Criterios de aceptación (medibles)
- [ ] Iniciar y terminar una llamada desde el navegador, en escritorio y celular (incl. Safari iOS).
- [ ] La llamada conecta y el agente saluda en < 2 s.
- [ ] La transcripción aparece en vivo (latencia visible < 1 s tras el texto parcial).
- [ ] Tras confirmar un pedido por voz, aparece en el panel en < 5 s.
- [ ] Los precios siempre vienen de `get_menu`; el total lo calcula el backend.
- [ ] Nunca se crea un pedido sin confirmación explícita.
- [ ] Plato agotado o inexistente no rompe la conversación.
- [ ] Pedidos y reservas repetidos (mismo `tool_call_id`) no se duplican.
- [ ] Reservas inválidas se rechazan con alternativa.
- [ ] Cada llamada queda guardada con transcripción, resumen y outcome.
- [ ] Peticiones sin secreto válido → 401.
- [ ] Tools responden en < 1 s (p95) en condiciones normales.
- [ ] Cada visitante ve solo sus datos.
- [ ] Errores (micrófono, conexión, servidor dormido) con mensajes claros.
- [ ] Sin claves privadas en el código ni en el repo; límites de gasto y duración configurados en Vapi.
- [ ] Funciona desplegado, no solo en local.
- [ ] Video, GIF de ~10 s, capturas y README listos para Upwork.

## Guion del video (1.5–2 min, subtítulos en inglés)
1. **0:00** Texto: "AI voice agent for a restaurant: takes orders, books tables, hands off to a human."
2. **0:08** Clic en "Call". Sofía saluda; transcripción en vivo.
3. **0:20** Pedido: "Quiero un lomo y dos jugos de maracuyá". El pedido se arma en el panel lateral; el agente repite y pide confirmación.
4. **0:40** Cambio: "Mejor que el lomo sea bien cocido". El agente corrige.
5. **0:55** Confirmación; el chip "✅ Pedido #N" y la tarjeta aparece en el tablero.
6. **1:10** Segunda llamada corta: reserva para 4.
7. **1:25** Pantalla de llamadas: resumen y transcripción guardados.
8. **1:35** Pantalla final con el stack: **Vapi, FastAPI, PostgreSQL, React**.

Antes de grabar: despertar el backend (ping a `/health`).

## README del repo (en inglés)
What it is · Live demo (aviso de micrófono y cold start) · Features · Architecture diagram · Tech stack · Screenshots/GIF · How to run · Environment variables · Notes ("demo uses fictional data").
