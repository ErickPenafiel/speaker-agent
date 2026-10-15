"""Imprime el JSON Schema de los parámetros de las tools, para pegarlo en Vapi o Retell.

uv run python -m scripts.print_tool_schemas
"""

import json

from app.schemas.orders import CreateOrderArgs
from app.schemas.reservations import CreateReservationArgs, TransferArgs

TOOLS = {
    "get_menu": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["parrilla", "criolla", "entradas", "bebidas", "postres"],
            },
            "query": {"type": "string", "description": "texto a buscar en el nombre del plato"},
        },
    },
    "create_order": CreateOrderArgs.model_json_schema(),
    "create_reservation": CreateReservationArgs.model_json_schema(),
    "transfer_to_human": TransferArgs.model_json_schema(),
}

if __name__ == "__main__":
    print(json.dumps(TOOLS, indent=2, ensure_ascii=False))
