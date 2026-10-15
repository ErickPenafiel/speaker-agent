class BusinessError(Exception):
    """Error esperable. El mensaje se devuelve al agente tal cual (corto, apto para voz)."""


class DemoReadOnlyError(Exception):
    """Se intentó modificar un dato de ejemplo (son de solo lectura)."""
