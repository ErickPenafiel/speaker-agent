"""SOLO DESARROLLO: guarda los payloads reales que mandan Vapi y Retell, para convertirlos en
fixtures de test. Desactivado salvo que `CAPTURE_PAYLOADS_DIR` esté definido. Contiene datos
personales de las llamadas: no usar en producción ni subir los archivos al repositorio sin anonimizarlos."""

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings

SAFE_HEADERS = {"content-type", "user-agent"}  # nunca se guardan secretos ni firmas


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2))


async def capture_payload(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    if not settings.capture_payloads_dir:
        return
    raw = await request.body()
    try:
        body = json.loads(raw)
    except ValueError:
        body = raw.decode(errors="replace")
    now = datetime.now(UTC)
    slug = re.sub(r"[^a-z0-9]+", "-", request.url.path.lower()).strip("-")
    record = {
        "path": request.url.path,
        "received_at": now.isoformat(),
        "headers": {k: v for k, v in request.headers.items() if k.lower() in SAFE_HEADERS},
        "body": body,
    }
    file = Path(settings.capture_payloads_dir) / f"{now:%Y%m%dT%H%M%S%f}-{slug}.json"
    await asyncio.to_thread(_write, file, record)
