# Backend (FastAPI): Agente de voz para restaurante (Vapi)

> Esta versión reemplaza el stack de `backend-voz.md` (NestJS) por **Python + FastAPI**. El caso de uso (La Brasa, agente Sofía), el modelo de datos, las tools, el prompt, el menú ficticio, los guiones de prueba y los criterios de aceptación **son los mismos**. Aquí solo cambia la implementación.
>
> Importante: los formatos de las tool calls y de los server messages de Vapi pueden cambiar. Verifica en su documentación oficial el formato actual de la petición y de la respuesta antes de implementar. Los ejemplos de abajo son una guía.

## 1. Caso de uso

**La Brasa**, restaurante ficticio de parrilla y comida criolla. El agente **Sofía** contesta en español: responde sobre menú y horarios, toma pedidos (con confirmación en voz alta antes de enviarlos), hace reservas y transfiere a una persona. Todos los datos son inventados.

## 2. Stack

| Capa | Elección | Nota |
|---|---|---|
| Voz | Vapi | llamada web gratis para probar |
| API | FastAPI + Uvicorn | |
| Validación | Pydantic v2 + pydantic-settings | |
| Base de datos | PostgreSQL en Neon | |
| ORM | SQLAlchemy 2.x async + asyncpg | |
| Migraciones | Alembic | |
| Rate limit | `slowapi` | para los endpoints del panel |
| Tests | `pytest` + `pytest-asyncio` + `httpx` | |
| Paquetes | `uv` o `poetry` | |
| Túnel en desarrollo | ngrok o Cloudflare Tunnel | Vapi necesita URL pública |
| Hosting | Render o Railway (Dockerfile) | avisar del cold start |

## 3. Arquitectura

```
[Navegador: Vapi Web SDK]  --voz-->  [Vapi: STT + LLM + TTS + interrupciones]
                                            |
                              tool calls + server messages (HTTPS POST)
                                            v
                                   [FastAPI (pública)]
                                     |-- routers/vapi      (tools + webhook)
                                     |-- routers/panel     (orders, reservations, calls, menu)
                                     |-- services/menu, orders, reservations, calls, transfer
                                            v
                                   [PostgreSQL (Neon)]
```

## 4. Estructura de carpetas

```
backend/
  app/
    main.py
    core/
      config.py             # Settings
      security.py           # verificación del secreto de Vapi, rate limit
      errors.py             # excepciones de negocio -> mensajes para el agente
    db/
      session.py
      models.py
      migrations/
    schemas/
      vapi.py               # modelos del payload de Vapi
      orders.py
      reservations.py
      calls.py
      menu.py
    routers/
      vapi.py               # POST /vapi/tools y POST /vapi/webhook
      orders.py
      reservations.py
      calls.py
      menu.py
      health.py
    services/
      menu_service.py
      order_service.py
      reservation_service.py
      call_service.py
      transfer_service.py
      tool_registry.py      # nombre de tool -> función
  seed/
    menu.py                 # menú ficticio de La Brasa
  tests/
  alembic.ini
  pyproject.toml
  Dockerfile
  .env.example
  README.md
```

## 5. Modelo de datos

Idéntico a `backend-voz.md`: `menu_items`, `orders`, `order_items`, `reservations`, `calls`, `transfers`. Ejemplo de pedidos con SQLAlchemy:

```python
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Text, Numeric, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, unique=True, autoincrement=True)  # número legible
    call_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String)
    customer_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String)            # pickup | delivery
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="confirmed")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
```

El campo `idempotency_key` (por ejemplo, el `toolCallId` de Vapi) evita crear pedidos duplicados si la petición llega dos veces.

## 6. Endpoints

**Para el agente (protegidos con secreto)**

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/vapi/tools` | recibe las tool calls y las enruta por nombre |
| POST | `/vapi/webhook` | server messages: reporte de fin de llamada y otros |

Se puede configurar el mismo servidor para ambos, o separarlos; sigue lo que indique la documentación actual de Vapi.

**Para el panel**

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/orders` | lista de pedidos |
| PATCH | `/orders/{id}/status` | cambiar estado |
| GET | `/reservations` | lista |
| GET | `/calls` | llamadas con resumen |
| GET | `/calls/{id}` | detalle con transcripción |
| GET | `/menu` | menú |
| GET | `/health` | estado |

## 7. Verificación del secreto

```python
# app/core/security.py
import hmac
from fastapi import Header, HTTPException, status
from app.core.config import settings

async def verify_vapi_secret(x_vapi_secret: str | None = Header(default=None)):
    if not x_vapi_secret or not hmac.compare_digest(x_vapi_secret, settings.vapi_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")
```

> El nombre exacto del header o del mecanismo de autenticación depende de cómo lo configures en Vapi; ajústalo a su documentación.

## 8. Router de tools

El patrón: un solo endpoint recibe las tool calls, ejecuta la función correspondiente y devuelve un resultado corto para que el agente lo diga o lo use.

```python
# app/routers/vapi.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_vapi_secret
from app.core.errors import BusinessError
from app.db.session import get_session
from app.services.tool_registry import TOOLS

router = APIRouter(prefix="/vapi", dependencies=[Depends(verify_vapi_secret)])

@router.post("/tools")
async def handle_tools(payload: dict, session: AsyncSession = Depends(get_session)):
    # Verifica el formato real en la documentación de Vapi.
    message = payload.get("message", {})
    tool_calls = message.get("toolCallList") or message.get("toolCalls") or []
    call_id = (message.get("call") or {}).get("id")

    results = []
    for tc in tool_calls:
        tool_call_id = tc.get("id")
        fn = tc.get("function", {})
        name = fn.get("name")
        args = fn.get("arguments") or {}

        handler = TOOLS.get(name)
        if handler is None:
            results.append({"toolCallId": tool_call_id, "result": "Herramienta no disponible."})
            continue
        try:
            text = await handler(session, args, call_id=call_id, tool_call_id=tool_call_id)
        except BusinessError as e:
            text = str(e)                 # mensaje corto que Sofía puede decir
        except Exception:
            text = "Hubo un problema técnico. Ofrece pasar con una persona."
        results.append({"toolCallId": tool_call_id, "result": text})

    return {"results": results}
```

```python
# app/services/tool_registry.py
from app.services import menu_service, order_service, reservation_service, transfer_service

TOOLS = {
    "get_menu": menu_service.get_menu_tool,
    "create_order": order_service.create_order_tool,
    "create_reservation": reservation_service.create_reservation_tool,
    "transfer_to_human": transfer_service.transfer_tool,
}
```

```python
# app/core/errors.py
class BusinessError(Exception):
    """Error esperable. El mensaje se devuelve al agente tal cual."""
```

## 9. Las 4 tools

Las respuestas deben ser **cortas y fáciles de decir en voz alta**. No devuelvas JSON enorme.

### `get_menu`
- Parámetros: `category?`, `query?`.
- Devuelve: platos con nombre, precio y alérgenos relevantes, en una frase.

### `create_order`
- Parámetros: `customer_name`, `type` (pickup | delivery), `address?`, `items[] { name, quantity, options?, notes? }`, `notes?`.
- Reglas:
  - Solo se llama después de que el cliente confirmó el resumen.
  - Validar que cada plato existe y está disponible; si no, `BusinessError("El lomo está agotado")`.
  - **Calcular el total en el backend**, nunca confiar en el LLM.
  - Idempotencia por `tool_call_id`.
- Devuelve: número de pedido, total y tiempo estimado.

```python
# app/schemas/orders.py
from typing import Literal
from pydantic import BaseModel, Field

class OrderItemIn(BaseModel):
    name: str
    quantity: int = Field(ge=1, le=20)
    options: dict | None = None
    notes: str | None = None

class CreateOrderArgs(BaseModel):
    customer_name: str = Field(min_length=2, max_length=80)
    type: Literal["pickup", "delivery"]
    address: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)
    notes: str | None = None
```

```python
# app/services/order_service.py (fragmento)
from pydantic import ValidationError
from app.core.errors import BusinessError
from app.schemas.orders import CreateOrderArgs

async def create_order_tool(session, args: dict, *, call_id, tool_call_id) -> str:
    try:
        data = CreateOrderArgs(**args)
    except ValidationError:
        raise BusinessError("Me faltan datos del pedido. Pregunta nombre y platos.")

    if data.type == "delivery" and not data.address:
        raise BusinessError("Para delivery necesito la dirección.")

    existing = await find_by_idempotency_key(session, tool_call_id)
    if existing:
        return f"Pedido {existing.number} ya registrado."

    order = await build_and_save_order(session, data, call_id, tool_call_id)  # valida platos y calcula total
    return f"Pedido {order.number} confirmado. Total {order.total} bolivianos. Estará listo en unos 25 minutos."
```

### `create_reservation`
- Parámetros: `customer_name`, `party_size`, `date`, `time`, `notes?`.
- Reglas: horario de atención, máximo de personas, fecha futura. Si no es válida, devolver una alternativa.
- Devuelve: confirmación con fecha y hora.

### `transfer_to_human`
- Parámetros: `reason`.
- En el demo: registra en `transfers` y el agente dice que te comunica con una persona (simulado). Vapi permite transferencia real a un número si más adelante la quieres.

## 10. Webhook de fin de llamada

```python
@router.post("/webhook")
async def webhook(payload: dict, session: AsyncSession = Depends(get_session)):
    message = payload.get("message", {})
    if message.get("type") == "end-of-call-report":
        await call_service.save_report(session, message)   # id, duración, transcripción, resumen
    return {"ok": True}
```

`save_report` debe:
1. Guardar el id de Vapi, duración, transcripción y resumen en `calls`.
2. Asignar `outcome` (pedido, reserva, info, transferida, abandonada).
3. Enlazar pedidos y reservas por `call_id`.

> Si el payload es grande, procesa lo pesado con `BackgroundTasks` y responde rápido.

## 11. Configuración

```python
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    vapi_webhook_secret: str
    frontend_origin: str
    restaurant_open: str = "12:00"
    restaurant_close: str = "23:00"
    max_party_size: int = 12

settings = Settings()
```

La clave **privada** de Vapi, si la necesitas en el servidor, va solo en variables de entorno del backend; en el frontend solo la pública.

## 12. `main.py` base

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import vapi, orders, reservations, calls, menu, health

app = FastAPI(title="La Brasa Voice API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(vapi.router)
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
app.include_router(calls.router, prefix="/calls", tags=["calls"])
app.include_router(menu.router, prefix="/menu", tags=["menu"])
```

## 13. Prompt, menú y guiones

Sin cambios: usa el **prompt de Sofía**, el **menú ficticio** (con 1 o 2 platos agotados) y los **12 guiones de prueba** de `backend-voz.md`. Son independientes del lenguaje del backend.

## 14. Seguridad y robustez

- Verificar el secreto en cada petición de Vapi.
- Validar todo con Pydantic; si falla, devolver un mensaje corto para el agente.
- Idempotencia en `create_order` y `create_reservation`.
- Respuesta de tools en menos de 1 segundo (usa `async` de punta a punta, conexiones reutilizadas, consultas con índices).
- `slowapi` en los endpoints del panel.
- Logs sin datos sensibles y datos del demo siempre ficticios.
- En Render gratis el servicio se duerme: haz un ping a `/health` antes de grabar el video o de una demostración, porque la **primera llamada con un servidor dormido puede fallar por timeout**.

## 15. Comandos

```bash
# Entorno (con uv)
uv init && uv add fastapi "uvicorn[standard]" pydantic-settings sqlalchemy asyncpg alembic slowapi

# Migraciones y seed
alembic upgrade head
python -m seed.menu

# Desarrollo
uvicorn app.main:app --reload --port 8000

# Túnel público para Vapi
ngrok http 8000        # o cloudflared tunnel

# Tests
pytest -q
```

### Dockerfile (base)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app ./app
COPY seed ./seed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 16. Tests mínimos

- `create_order` con plato válido: crea el pedido y calcula el total en el backend.
- `create_order` con plato agotado: devuelve mensaje de error, no crea pedido.
- `create_order` repetido con el mismo `tool_call_id`: no duplica.
- `create_reservation` fuera de horario o para 20 personas: rechaza con alternativa.
- Petición sin secreto: 401.
- Webhook de fin de llamada: guarda transcripción y resumen.

## 17. Plan por días

| Día | Entregable |
|---|---|
| 1 | Proyecto FastAPI, Neon, modelos y migraciones, seed del menú, `get_menu`, túnel público. Asistente en Vapi con prompt y llamada web funcionando |
| 2 | `create_order` (validaciones, total, idempotencia), `create_reservation`, `transfer_to_human`, webhook de fin de llamada, secreto verificado |
| 3 | Endpoints del panel, tests, los 12 guiones de prueba y ajustes del prompt, despliegue con Docker en Render, README |

## 18. Criterios de aceptación

- [ ] `/docs` muestra los endpoints del panel y los de Vapi.
- [ ] La llamada web conecta y el agente saluda en menos de 2 segundos.
- [ ] Los precios siempre vienen de `get_menu`.
- [ ] Nunca se crea un pedido sin confirmación explícita.
- [ ] Un plato agotado o inexistente se maneja sin romper la conversación.
- [ ] Los pedidos repetidos no se duplican.
- [ ] Las reservas inválidas se rechazan con una alternativa.
- [ ] Cada llamada queda guardada con transcripción y resumen.
- [ ] Las peticiones sin secreto válido devuelven 401.
- [ ] Las tools responden en menos de 1 segundo en condiciones normales.
- [ ] Funciona desplegado, no solo en local.

## 19. Qué cambia en el frontend

Nada. `frontend-voz.md` sigue igual: las rutas del panel son las mismas. Solo ajusta `VITE_API_URL` al nuevo backend.
