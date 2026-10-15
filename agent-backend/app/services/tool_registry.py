from collections.abc import Awaitable, Callable

from app.services import menu_service, order_service, reservation_service, transfer_service

# Firma: handler(session, args, *, call_id, tool_call_id, session_id) -> str
ToolHandler = Callable[..., Awaitable[str]]

TOOLS: dict[str, ToolHandler] = {
    "get_menu": menu_service.get_menu_tool,
    "create_order": order_service.create_order_tool,
    "create_reservation": reservation_service.create_reservation_tool,
    "transfer_to_human": transfer_service.transfer_tool,
}
