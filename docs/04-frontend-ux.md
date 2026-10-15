# 4. Frontend y UX/UI

## Pantallas

### A. Llamar (principal) — layout dividido
- **Escritorio**: izquierda la llamada, derecha el **pedido armándose en vivo** (los platos aparecen cuando el agente los confirma). En **móvil**: una columna, panel en drawer o pestañas inferiores.
- **Orbe de voz** como protagonista, 4 estados: inactivo, conectando, escuchando (pulso suave), hablando (escala con el evento `volume-level` del SDK; animado con Motion).
- Botón principal grande, alcanzable con el pulgar; "Colgar" durante la llamada; silenciar micrófono.
- **Transcripción** tipo chat: texto parcial en gris que se vuelve sólido al finalizar (reemplazar el parcial por el final, no añadir duplicados). `aria-live`.
- **Chips de tools** en la transcripción: "🔧 Creando pedido…" → "✅ Pedido #12".
- **Selector de idioma del agente (EN/ES)** y tarjeta "Qué puedes probar": frases clicables en español con su traducción al inglés.
- Wake lock en móvil durante la llamada.
- Banner discreto: "Demo con datos ficticios · Voice demo in Spanish/English".

### B. Pedidos — estilo cocina
Kanban de 3 columnas (Confirmado, Preparando, Listo); cambio de estado con botones (dnd-kit opcional). Pedido nuevo entra con animación y resaltado unos segundos. Modo oscuro tipo pantalla de cocina.

### C. Reservas — lista por fecha/hora con personas y notas.
### D. Llamadas — lista (fecha, duración, outcome, resumen) y detalle con transcripción completa y enlaces al pedido/reserva.
### E. Menú — solo lectura; puede ser un diálogo (baja prioridad, recortar si falta tiempo).

## Proveedor de voz intercambiable
Interfaz común `VoiceAdapter` (`start`, `stop`, `setMuted`, eventos normalizados: `connected`, `ended`, `agentSpeaking`, `userSpeaking`, `volume`, `transcript{role, text, final}`, `toolResult`, `error`). Dos implementaciones, cargadas con `import()` dinámico según `provider`:
- `VapiAdapter` (`@vapi-ai/web`): `vapi.start(assistantId, overrides)` con `public_key` y `metadata`.
- `RetellAdapter` (`retell-client-js-sdk`): `startCall({accessToken})`.
Los eventos nativos de cada SDK se traducen a los normalizados; el resto de la UI no sabe qué proveedor hay. Variable única: `VITE_API_URL`.

## Flujo de la llamada
1. Al cargar la página: **ping automático a `/health`** con reintentos e indicador ("Despertando el servidor…") antes de habilitar el botón.
2. Pulsar "Llamar" → permiso de micrófono (gesto del usuario; importante en iOS Safari).
3. `POST /voice/web-call {session_id, language}` → según `provider`, iniciar el adaptador correspondiente.
4. Eventos del SDK: inicio, fin, habla del agente/usuario, `volume-level`, mensajes de transcripción, resultados de tools, errores.
5. **Al llegar el resultado de una tool** → `invalidateQueries(['orders'])` (los pedidos existen ya durante la llamada).
6. **Al terminar** → refrescar `calls` con reintentos unos segundos (el reporte final llega con retraso). Polling más rápido (~2 s) por ~1 min tras la llamada y solo con la pestaña visible.

## Estados y errores

| Situación | Qué se muestra |
|---|---|
| Micrófono denegado | explicación y cómo habilitarlo |
| Fallo al iniciar / sin conexión | mensaje claro + "Reintentar" |
| Backend dormido | "Despertando el servidor (~30 s)" y botón deshabilitado hasta `/health` OK |
| Llamada cortada | transcripción hasta ese punto |
| Pedido aún no aparece | "procesando" + reintento automático |
| Navegador no compatible | sugerir Chrome/Edge; **probar Safari iOS** (mucho tráfico móvil) |

## Detalles de calidad
Skeletons en vez de spinners; estados vacíos con CTA; `prefers-reduced-motion`; tema claro/oscuro; foco visible; Inter o Geist y un único acento cálido (naranja parrilla) con tokens de shadcn.

## Estructura (✅ = ya creado)

```
agent-frontend/src/
  main.tsx ✅  App.tsx ✅ (placeholder)  index.css ✅ (Tailwind v4)
  app/ routes.tsx  queryClient.ts
  features/
    call/  CallPage  VoiceOrb  CallButton  LiveTranscript  LiveOrderPanel  TryIdeas  LanguageSelect  useVapiCall.ts
    orders/ OrdersBoard  OrderCard  StatusSelect
    reservations/ ReservationsPage
    calls/ CallsPage  CallDetail
    menu/ MenuDialog
  components/ui/            (shadcn)
  lib/ api.ts  api-types.ts (generado: pnpm gen:api)  session.ts
  mocks/ (MSW)
```
`.env.example`: `VITE_API_URL`, `VITE_VAPI_PUBLIC_KEY`, `VITE_VAPI_ASSISTANT_ID`.

## Textos
UI en inglés sencillo para Upwork; el agente habla ES o EN según el selector.

## Tests
Vitest + Testing Library para el reducer de transcripción y componentes clave; **un** flujo de humo con Playwright y Vapi mockeado.
