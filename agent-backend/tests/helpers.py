import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str, **subs: str) -> dict:
    """Carga un fixture JSON sustituyendo los marcadores {{CLAVE}}."""
    text = (FIXTURES / name).read_text()
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", value)
    return json.loads(text)
