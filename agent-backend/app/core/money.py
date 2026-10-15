from decimal import Decimal

from app.core.config import get_settings


def format_money(amount: Decimal) -> str:
    """Apto para voz: sin decimales si es entero ("78 BOB"), con dos si no ("12.50 BOB")."""
    value = f"{amount:.0f}" if amount == amount.to_integral_value() else f"{amount:.2f}"
    return f"{value} {get_settings().currency}"
