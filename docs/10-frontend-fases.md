# 10. Frontend: plan por fases

Cada fase termina con componentes o flujos que se pueden **ejecutar, renderizar y probar**. No se avanza a la siguiente sin tests unitarios/componentes en verde (`pnpm test`) y validación de tipos y lint (`pnpm lint` / `pnpm build`).

| Fase | Entregable | Estado |
|---|---|---|
| 0 | Esqueleto tipado: tipos OpenAPI, sesión (`X-Session-Id`), cliente API y TanStack Query | ✅ Hecha |
| 1 | Capa de voz multi-proveedor: `VoiceAdapter` (Vapi / Retell), hook `useVoiceCall`, reducer de transcripción | ✅ Hecha |
| 2 | Pantalla de llamada en vivo: `VoiceOrb` animado, transcripción en streaming con chips, panel de pedido en vivo y control de micrófono | ✅ Hecha |
| 3 | Panel de pedidos estilo cocina: Kanban (Confirmado, Preparando, Listo), cambio de estado, animación de nuevos y soporte `is_demo` | ✅ Hecha |
| 4 | Reservas, Historial de llamadas y Menú: lista con detalle de transcripción, enlaces a pedidos/reservas y visor de menú | ✅ Hecha |
| 5 | Experiencia global, navegación y diseño "La Brasa": layout dividido, tema oscuro cálido, indicador de servidor dormido y toasts de error/rate limit | ✅ Hecha |
| 6 | Verificación integral, tests y despliegue: suite Vitest completa, prueba de humo en navegador, build optimizado y documentación | ✅ Hecha |

---

## Fase 0 — Esqueleto tipado, sesión, cliente API y MSW

### Objetivo
Establecer el contrato estricto con el backend de FastAPI, la inyección transparente del header `X-Session-Id` y un entorno de desarrollo desacoplado con mocks realistas (MSW).

### Tareas y Archivos
1. **Identificador de Sesión (`src/lib/session.ts`)**:
   - Generación de UUIDv4 con `crypto.randomUUID()` si no existe en `localStorage`.
   - Clave persistida: `speaker_agent_session_id`.
   - Función `getSessionId(): string` que garantiza una cadena válida de 36 caracteres compatible con el backend (`[A-Za-z0-9_-]{16,64}`).
2. **Tipos de la API (`src/lib/api-types.ts` o `src/lib/types.ts`)**:
   - Tipos TypeScript alineados con los esquemas Pydantic del backend:
     - `MenuItem`, `MenuResponse`.
     - `OrderItem`, `OrderLine`, `OrderResponse`, `OrderStatus` (`confirmed` | `preparing` | `ready`).
     - `ReservationItem`, `ReservationResponse`.
     - `CallItem`, `CallDetailResponse`, `CallOutcome` (`order` | `reservation` | `transferred` | `info` | `abandoned`).
     - `WebCallInfo`: `{ provider: 'vapi', assistant_id: string, public_key: string }` | `{ provider: 'retell', access_token: string }`.
     - Flags de `is_demo: boolean` en respuestas de entidades.
3. **Cliente HTTP Tipado (`src/lib/api.ts`)**:
   - Wrapper sobre `fetch` o `openapi-fetch` que inyecta automáticamente:
     - `X-Session-Id: getSessionId()` en todas las peticiones a endpoints protegidos (`/orders`, `/reservations`, `/calls`).
     - Manejo estandarizado de respuestas de error:
       - `429 Too Many Requests`: extracción del header `Retry-After`.
       - `403 Forbidden`: acción no permitida sobre registros demo (`is_demo`).
       - `503 Service Unavailable`: backend o base de datos en reposo / iniciando.
4. **Configuración de TanStack Query (`src/app/queryClient.ts`)**:
   - `staleTime` razonable (10 s para panel de pedidos, 30 s para menú).
   - Reintentos exponenciales con límite (máximo 2 intentos para evitar saturar el backend).
5. **Mocks con MSW (`src/mocks/handlers.ts` y `src/mocks/browser.ts`)**:
   - Handlers para `/health`, `/voice/config`, `/voice/web-call`, `/menu`, `/orders`, `/reservations`, `/calls`.
   - Datos idénticos a los del seed del backend (con ejemplos marcados con `is_demo: true`).

### Criterio de Salida
- `src/lib/session.ts` genera y recupera la misma sesión en recargas.
- Tests unitarios de `api.ts` comprobando que el header `X-Session-Id` se envía y que los errores 403, 429 y 503 se parsean correctamente.
- Servidor MSW funcionando en tests con Vitest.

---

## Fase 1 — Capa de voz multi-proveedor (`VoiceAdapter`)

### Objetivo
Aislar la interfaz de usuario de las peculiaridades de cada SDK de voz (`@vapi-ai/web` frente a `retell-client-js-sdk`). El resto de la aplicación sólo interactúa con una interfaz unificada.

### Diseño de la Capa de Adaptador
```typescript
export interface VoiceCallConfig {
  sessionId: string;
  language: 'es' | 'en';
}

export type VoiceCallState = 'idle' | 'connecting' | 'listening' | 'speaking';

export interface TranscriptMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isFinal: boolean;
  timestamp: Date;
}

export interface ToolCallEvent {
  toolName: string;
  status: 'running' | 'completed' | 'failed';
  message?: string;
  orderId?: number;
}

export interface VoiceAdapter {
  start(config: VoiceCallConfig): Promise<void>;
  stop(): Promise<void>;
  setMuted(muted: boolean): void;
  isMuted(): boolean;
  on(event: 'stateChange', cb: (state: VoiceCallState) => void): void;
  on(event: 'volume', cb: (volume: number) => void): void; // 0.0 a 1.0
  on(event: 'transcript', cb: (msg: TranscriptMessage) => void): void;
  on(event: 'toolCall', cb: (tool: ToolCallEvent) => void): void;
  on(event: 'error', cb: (error: Error) => void): void;
  destroy(): void;
}
```

### Implementaciones
1. **`VapiAdapter` (`src/features/call/adapters/vapiAdapter.ts`)**:
   - Inicializa `@vapi-ai/web` con `public_key` y `assistant_id`.
   - Traduce eventos:
     - `call-start` → `state: 'listening'`.
     - `call-end` → `state: 'idle'`.
     - `speech-start` (asistente) → `state: 'speaking'`.
     - `speech-end` → `state: 'listening'`.
     - `volume-level` → evento normalizado de volumen (0.0 a 1.0).
     - `message` (type `transcript`, roles `user` y `assistant`) con discriminación de `transcriptType: 'partial' | 'final'`.
     - `message` (type `function-call` / `tool-calls`) para detectar creación de pedidos/reservas en vivo.
2. **`RetellAdapter` (`src/features/call/adapters/retellAdapter.ts`)**:
   - Diseñado para recibir `access_token` desde `POST /voice/web-call`.
   - Mapeo de eventos homólogos al formato normalizado.
3. **Reducer de Transcripción (`src/features/call/transcriptReducer.ts`)**:
   - Deduplicación estricta: un mensaje parcial entrante reemplaza al parcial anterior del mismo rol; al recibir `isFinal: true`, se consolida en la lista histórica.
   - Vinculación de chips de tool (`🔧 Creando pedido...` → `✅ Pedido #12`).
4. **Hook React `useVoiceCall` (`src/features/call/useVoiceCall.ts`)**:
   - Gestiona permisos de micrófono con feedback explicativo de error (`NotAllowedError`).
   - Controla Screen Wake Lock (`navigator.wakeLock`) para evitar que la pantalla se apague durante la llamada en móviles.
   - Sincroniza el estado del audio y volumen reactivo.

### Criterio de Salida
- Tests unitarios exhaustivos para `transcriptReducer`:
  - Reemplazo de texto parcial por parcial nuevo sin duplicados.
  - Consolidación de texto final.
  - Inserción de chips de herramientas en el flujo.
- Test del adapter con SDK simulado.

---

## Fase 2 — Pantalla de llamada en vivo (Call Page)

### Objetivo
Construir el núcleo interactivo que impacta en los primeros 30 segundos de uso: layout dividido con orbe de voz reactivo, transcripción en vivo tipo chat y panel lateral con el pedido armándose en tiempo real.

### Componentes y Funcionalidades
1. **Orbe de Voz (`src/features/call/components/VoiceOrb.tsx`)**:
   - 4 estados visuales claros mediante animaciones de Motion:
     - `idle`: respiración suave y tenue en tonos cálidos.
     - `connecting`: rotación o pulso acelerado.
     - `listening`: onda suave receptiva.
     - `speaking`: expansión reactiva ligada al volumen del audio (`volume-level`).
   - Accesibilidad: soporte para `prefers-reduced-motion`.
2. **Controles de Llamada (`src/features/call/components/CallControls.tsx`)**:
   - Botón principal de tamaño táctil amplio ("Llamar a La Brasa" / "Colgar").
   - Botón de silenciar micrófono con icono dinámico (Mic / MicOff).
   - Selector de idioma del agente (`LanguageSelect`: Español / Inglés).
3. **Transcripción en Vivo (`src/features/call/components/LiveTranscript.tsx`)**:
   - Vista tipo conversación con burbujas diferenciadas para usuario y agente.
   - Texto parcial en gris que se transforma en blanco/sólido al finalizar.
   - Chips visuales de herramientas intercalados:
     - 🔧 *Verificando menú...*
     - 📝 *Preparando pedido...*
     - ✅ *Pedido #15 confirmado ($24.50)*
   - Región accesible con `aria-live="polite"`.
4. **Panel de Pedido en Vivo (`src/features/call/components/LiveOrderPanel.tsx`)**:
   - Visible en split-screen en escritorio; en pestaña o drawer en móvil.
   - Muestra los platos que el cliente va solicitando antes o inmediatamente después de que el webhook los inserte.
   - Resalta el total acumulado y estado de confirmación.
5. **Tarjeta de Ideas Rápidas (`src/features/call/components/TryIdeas.tsx`)**:
   - 4 sugerencias accionables con un clic (ej. *"Pide un lomo y dos jugos"*, *"Reserva para 4 mañana a las 20:00"*).
   - Texto en español con subtítulo explicativo en inglés.
6. **Manejo de Permisos y Errores**:
   - Alerta visual amigable con pasos para habilitar el micrófono si fue bloqueado en Chrome o Safari iOS.

### Criterio de Salida
- La pantalla de llamada renderiza el orbe respondiendo a cambios de estado simulados.
- El panel de pedido en vivo actualiza sus elementos al emitir eventos de tool.
- Verificación en Vitest del comportamiento de la transcripción en vivo.

---

## Fase 3 — Panel de pedidos estilo cocina (Kitchen Kanban)

### Objetivo
Visualización y control de pedidos en tiempo real con estética de pantalla de cocina de restaurante.

### Componentes y Reglas
1. **Tablero Kanban (`src/features/orders/components/OrdersBoard.tsx`)**:
   - 3 columnas: **Confirmado**, **Preparando**, **Listo**.
   - Cada columna con contador de pedidos activos.
2. **Tarjeta de Pedido (`src/features/orders/components/OrderCard.tsx`)**:
   - Número de pedido (`#12`), cliente, hora de recepción.
   - Desglose de ítems (nombre del plato, cantidad, notas de cocción o variantes).
   - Tipo de entrega con badge: `Recoger` (pickup) o `A domicilio` (delivery con dirección).
   - Total formateado en moneda local.
   - Botones rápidos de avance de estado: `Confirmado → Iniciar preparación` / `Preparando → Marcar listo`.
3. **Gestión de Registros Demo (`is_demo`)**:
   - Si `is_demo === true`, se muestra un badge sutil `"Ejemplo"`.
   - Los botones de cambio de estado se deshabilitan con tooltip informativo: *"Los pedidos de ejemplo son de solo lectura"*.
4. **Actualización Reactiva e Invalidación**:
   - Polling automático periódico (`refetchInterval: 3000` durante llamada o tras finalizar).
   - Al recibir evento de tool exitosa desde la llamada, invalidación inmediata: `queryClient.invalidateQueries({ queryKey: ['orders'] })`.
   - Animación de entrada (destello cálido durante 3 segundos) para pedidos recién insertados.

### Criterio de Salida
- Test de renderizado del tablero con pedidos mock.
- Test de la mutación de estado con llamada a `PATCH /orders/:id/status`.
- Verificación del bloqueo de edición en pedidos `is_demo`.

---

## Fase 4 — Reservas, Historial de llamadas y Menú

### Objetivo
Permitir la consulta completa de reservas agendadas, auditoría detallada de llamadas de voz y referencia rápida del menú del restaurante.

### Vistas y Funcionalidades
1. **Página de Reservas (`src/features/reservations/ReservationsPage.tsx`)**:
   - Tabla o lista de tarjetas ordenadas cronológicamente por fecha y hora.
   - Columnas/datos: fecha, hora, comensales (pax), nombre del cliente, notas especiales.
   - Badge "Ejemplo" para reservas de la sesión demo.
2. **Página de Historial de Llamadas (`src/features/calls/CallsPage.tsx`)**:
   - Listado con fecha/hora, duración (formato `mm:ss`), resumen ejecutivo y outcome con badges codificados por color:
     - `order` (verde esmeralda)
     - `reservation` (azul cielo)
     - `transferred` (ámbar)
     - `info` (gris neutro)
     - `abandoned` (rojo tenue)
   - Clic en una fila abre el detalle.
3. **Detalle de Llamada (`src/features/calls/CallDetailDialog.tsx`)**:
   - Diálogo o drawer con la **transcripción completa de la conversación**.
   - Enlaces directos clicables al pedido o reserva generados en esa llamada.
   - Resumen generado por la IA.
4. **Diálogo de Menú (`src/features/menu/MenuDialog.tsx`)**:
   - Modal de consulta rápida cargado desde `GET /menu`.
   - Clasificación por categorías (Platos principales, Guarniciones, Bebidas).
   - Indicador visual claro para platos marcados como agotados (`is_available === false`).

### Criterio de Salida
- Navegación fluida al detalle de llamada con carga de transcripción.
- Renderizado correcto del menú respetando platos agotados.
- Tests unitarios de los filtros y badges de outcome.

---

## Fase 5 — Experiencia global, navegación y diseño "La Brasa"

### Objetivo
Integrar todas las vistas en una aplicación cohesiva con identidad visual premium, diseño responsivo móvil-primero y retroalimentación clara de estados de infraestructura.

### Sistema de Diseño y Layout
1. **Identidad Visual "La Brasa"**:
   - Paleta de colores: Base oscura profunda (Slate 950 / Zinc 900), fondos de tarjeta de vidrio suave (*subtle glassmorphism*), tipografía limpia (Inter / Geist) y color de acento cálido (*Flame Orange / Ember Amber*).
   - Componentes consistentes vía `shadcn/ui` y Tailwind CSS v4.
2. **Estructura de Navegación (`src/app/Layout.tsx` & `Navbar.tsx`)**:
   - Barra superior en escritorio: Logo "La Brasa", enlaces a *Llamada*, *Cocina (Pedidos)*, *Reservas*, *Llamadas*, botón para ver *Menú*, e indicador de estado de sesión.
   - Navegación inferior fija (*Bottom Nav*) para pantallas táctiles en móvil.
3. **Detector de Backend Dormido y Ping de Salud (`src/features/system/ServerWakeBanner.tsx`)**:
   - Verificación proactiva contra `GET /health` y `GET /health/ready` al montar la aplicación.
   - Si el backend tarda > 1.5 s o retorna 503 (cold start de tiers gratuitos como Render):
     - Banner o modal discreto: *"Despertando el servidor del restaurante (~20-30 s)..."*.
     - Deshabilita temporalmente el botón de llamar para evitar errores de conexión al usuario.
4. **Manejo Global de Errores y Notificaciones (Sonner)**:
   - Toasts elegantes cuando:
     - El rate limit se alcanza (429 con mensaje *"Límite alcanzado, reintente en X segundos"*).
     - La conexión se interrumpe.
     - Un pedido se confirma por voz exitosamente.

### Criterio de Salida
- Navegación interactiva funcional entre todas las rutas.
- Responsividad probada en viewports de móvil (375px) y escritorio (1280px+).
- Banner de "Despertando servidor" probado con estados de red simulados.

---

## Fase 6 — Verificación integral, tests y despliegue

### Objetivo
Asegurar que la aplicación compila limpiamente, cumple con todos los criterios de aceptación y está lista para el despliegue en producción y la grabación de la demo en video.

### Tareas de Validación
1. **Suite de Tests Automatizados (`pnpm test`)**:
   - Reducer de transcripción: deduplicación y formateo.
   - Sesión persistente y cabeceras de API.
   - Renderizado del orbe de voz y sus 4 estados.
   - Tablero Kanban y deshabilitación en modo solo lectura.
2. **Suite de Tests End-to-End (`pnpm test:e2e` con Playwright)**:
   - `e2e/home-call.spec.ts`: Carga de home, branding genérico, controles de llamada, selector de idiomas y panel de pedidos en vivo.
   - `e2e/menu.spec.ts`: Apertura de diálogo de menú, consulta en tiempo real al backend y verificación de platos.
   - `e2e/orders.spec.ts`: Navegación al tablero de cocina, visualización de columnas Kanban y pedidos activos.
   - `e2e/reservations.spec.ts`: Navegación y consulta del libro de reservas conectado al backend.
   - `e2e/calls.spec.ts`: Historial de llamadas, diálogo de detalle, resumen ejecutivo y transcripción con roles genéricos.
   - `e2e/theme.spec.ts`: Alternancia de tema (claro/oscuro) e indicador de sesión.
3. **Pruebas de Humo de Flujo de Llamada**:
   - Simulación del flujo completo: Llamar → Transcripción en vivo → Tool `create_order` recibida → Pedido visible en panel lateral → Colgar llamada → Historial de llamada actualizado.
3. **Verificación en Safari iOS y Chrome**:
   - Verificación de que la llamada de voz se inicia únicamente mediante un gesto del usuario (`click`/`touch`).
   - Verificación del comportamiento del micrófono y audio.
4. **Build y Despliegue**:
   - `pnpm build` sin errores de TypeScript (`tsc -b`) ni advertencias de lint.
   - Configuración de variables de entorno para Vercel:
     - `VITE_API_URL`
     - `VITE_VAPI_PUBLIC_KEY`
     - `VITE_VAPI_ASSISTANT_ID`
   - Configuración de SPA rewrites en `vercel.json` si aplica.

### Criterio de Salida Final
- Build en verde: `pnpm build` genera el bundle en `dist/` sin errores.
- Todos los tests unitarios pasando (`pnpm test`).
- Aplicación lista para el guion de video de 1.5 a 2 minutos para Upwork.
