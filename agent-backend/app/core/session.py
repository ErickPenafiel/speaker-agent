from typing import Annotated

from fastapi import Header

# Sesión reservada para los datos de ejemplo. Tiene 4 caracteres y el header exige 16-64, así que
# ningún cliente puede reclamarla.
DEMO_SESSION = "demo"
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"

# El id de sesión actúa como credencial del visitante: el frontend debe generarlo con
# `crypto.randomUUID()` y guardarlo en localStorage.
SessionId = Annotated[
    str,
    Header(
        alias="X-Session-Id",
        pattern=SESSION_ID_PATTERN,
        description="Id aleatorio del visitante (16-64 caracteres: letras, números, _ y -)",
    ),
]
