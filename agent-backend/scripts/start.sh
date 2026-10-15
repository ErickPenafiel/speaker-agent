#!/bin/sh
# Arranque del contenedor. Opcionales (desactivados por defecto):
#   RUN_MIGRATIONS=1  aplica `alembic upgrade head` (usar con UNA sola instancia: Alembic no bloquea)
#   SEED_ON_START=1   siembra menú y datos de ejemplo (idempotente; además refresca las fechas)
set -e
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  alembic upgrade head
fi
if [ "${SEED_ON_START:-0}" = "1" ]; then
  python -m seed.demo
fi
# Una sola instancia/proceso: el rate limit y el tope diario viven en memoria.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*' --no-access-log
