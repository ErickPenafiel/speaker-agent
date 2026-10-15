# Frontend: Agente de voz para restaurante (React + Vapi Web SDK)

> Nota: verifica en la documentación oficial de Vapi el uso actual del SDK web (inicialización, eventos, claves públicas).

## 1. Objetivo

Dos cosas en una sola app:
1. **Probar al agente**: un botón de llamar desde el navegador, con transcripción en vivo.
2. **Ver el resultado**: panel de pedidos, reservas y llamadas del restaurante **La Brasa** (ficticio), actualizado después de cada llamada.

Para el cliente de Upwork esto es lo importante: en 30 segundos escucha al agente y ve cómo el pedido aparece en el panel.

## 2. Stack

| Tema | Elección |
|---|---|
| Framework | React + Vite + TypeScript |
| Estilos | Tailwind CSS (+ shadcn/ui) |
| Voz | `@vapi-ai/web` (SDK de Vapi) |
| Datos del servidor | TanStack Query (con refetch periódico) |
| Estado local | Zustand o `useReducer` |
| Hosting | Vercel |

## 3. Pantallas

### A. Llamar (pantalla principal)
- Botón grande **"Llamar a La Brasa"**; cambia a "Colgar" durante la llamada.
- Estado visible: conectando, escuchando, hablando, llamada terminada.
- Indicador de audio (onda simple o círculo que pulsa cuando habla el agente).
- **Transcripción en vivo**: mensajes del cliente y de Sofía, con el texto parcial que va apareciendo.
- Botón de silenciar micrófono.
- Tarjeta lateral "Qué puedes probar": 4 ideas ("Pide un lomo y dos jugos", "Reserva para 4 mañana a las 8", "Pregunta por alergias", "Pide hablar con una persona").
- Aviso de permisos de micrófono, con instrucciones si fueron denegados.

### B. Pedidos
- Tabla o tarjetas tipo cocina: número, cliente, platos, tipo (recoger o delivery), total, estado.
- Cambiar estado (confirmado -> preparando -> listo).
- Se actualiza solo cada pocos segundos; el pedido nuevo aparece resaltado.

### C. Reservas
- Lista por fecha y hora, con personas y notas.

### D. Llamadas
- Lista con fecha, duración, resultado (pedido, reserva, info, transferida) y resumen.
- Detalle con **transcripción completa** y enlaces al pedido o reserva generados.

### E. Menú
- Vista de solo lectura del menú ficticio (sirve para comparar lo que dice el agente).

## 4. Flujo de la llamada web

1. Al pulsar "Llamar", pedir permiso de micrófono.
2. Iniciar la llamada con el SDK usando la **clave pública** de Vapi y el id del asistente (variables de entorno del frontend).
3. Escuchar los eventos del SDK: inicio de llamada, fin, habla del agente, habla del usuario, mensajes de transcripción, errores.
4. Mostrar la transcripción a medida que llega.
5. Al terminar la llamada, refrescar pedidos, reservas y llamadas (el backend recibe el reporte final con un pequeño retraso, así que reintentar durante unos segundos).

> La clave **privada** de Vapi jamás va en el frontend. Solo la pública.

## 5. Estados y errores que hay que cuidar

| Situación | Qué se muestra |
|---|---|
| Micrófono denegado | explicación y cómo habilitarlo en el navegador |
| Sin conexión o fallo al iniciar | mensaje claro con botón "Reintentar" |
| Backend dormido (free tier) | "Despertando el servidor, puede tardar ~30 s" antes de permitir llamar |
| Llamada cortada | mostrar la transcripción hasta ese punto |
| Pedido aún no aparece | indicador "procesando" y reintento automático |
| Navegador no compatible | sugerir Chrome o Edge reciente |

Recomendación: botón "Probar conexión" que llama a `/health` del backend antes de iniciar.

## 6. Componentes

```
src/
  main.tsx
  app/
    routes.tsx
    queryClient.ts
  features/
    call/
      CallPage.tsx
      CallButton.tsx
      AudioIndicator.tsx
      LiveTranscript.tsx
      TryIdeas.tsx
      useVapiCall.ts        # lógica del SDK y eventos
    orders/
      OrdersPage.tsx
      OrderCard.tsx
      StatusSelect.tsx
    reservations/
      ReservationsPage.tsx
    calls/
      CallsPage.tsx
      CallDetail.tsx
    menu/
      MenuPage.tsx
  components/ui/
  lib/
    api.ts
    types.ts
  .env.example            # VITE_API_URL=, VITE_VAPI_PUBLIC_KEY=, VITE_VAPI_ASSISTANT_ID=
```

## 7. Contrato con el backend

- `GET /orders`, `PATCH /orders/:id/status`
- `GET /reservations`
- `GET /calls`, `GET /calls/:id`
- `GET /menu`
- `GET /health`

Definir tipos compartidos en `lib/types.ts`. Mientras el backend no esté listo, usar datos mock con la misma forma.

## 8. Diseño

- Estilo limpio y cálido, con un color de acento (naranja o rojo parrilla).
- Pantalla de llamada centrada y simple; el panel, denso pero ordenado.
- Móvil primero: la llamada debe funcionar bien en un celular.
- Textos de la interfaz en **inglés sencillo** para el público de Upwork (el agente habla en español; indícalo: "Voice demo in Spanish").
- Accesibilidad: foco visible, `aria-live` para la transcripción, botones con etiquetas claras.

## 9. Plan por días

| Día | Entregable |
|---|---|
| 1 | Proyecto Vite y Tailwind, layout, cliente API con tipos y mocks, pantalla de llamada con el SDK y transcripción en vivo |
| 2 | Pedidos, reservas y llamadas con datos reales, refetch automático, estados de error y backend dormido |
| 3 | Pulido responsive, vista de detalle de llamada, menú, deploy en Vercel, capturas y video |

El día 1 puede avanzar sin el backend usando mocks, y se conecta cuando las tools estén listas.

## 10. Guion del video (1.5 a 2 minutos, con subtítulos)

1. **0:00** Texto: "AI voice agent for a restaurant: takes orders, books tables, hands off to a human."
2. **0:08** Clic en "Llamar". El agente saluda. Se ve la transcripción en vivo.
3. **0:20** Pedido: "Quiero un lomo y dos jugos de maracuyá". El agente repite y pide confirmación.
4. **0:40** Cambio a mitad: "Mejor que el lomo sea bien cocido". El agente corrige.
5. **0:55** Confirmación. Cortar a la pestaña de pedidos: aparece el pedido nuevo.
6. **1:10** Segunda llamada corta: una reserva para 4 personas.
7. **1:25** Pantalla de llamadas: resumen y transcripción guardados.
8. **1:35** Pantalla final con el stack: Vapi, NestJS, PostgreSQL, React.

Mientras se habla en español, pon subtítulos en inglés en pantalla.

## 11. README (en inglés)

Secciones: What it is, Live demo (con aviso de micrófono y cold start), Features, Architecture diagram, Tech stack, Screenshots/GIF, How to run (frontend), Environment variables, Notes ("demo uses fictional data").

## 12. Criterios de aceptación

- [ ] Se puede iniciar y terminar una llamada desde el navegador, en escritorio y celular.
- [ ] La transcripción aparece en vivo.
- [ ] Tras confirmar un pedido por voz, aparece en el panel en pocos segundos.
- [ ] Las reservas y llamadas guardadas se pueden consultar con su transcripción.
- [ ] Los errores (micrófono, conexión, servidor dormido) tienen mensajes claros.
- [ ] No hay claves privadas en el código ni en el repositorio.
- [ ] Hay video, capturas y README listos para subir a Upwork.
