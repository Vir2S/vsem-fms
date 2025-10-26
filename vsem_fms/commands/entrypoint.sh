#!/bin/bash
set -e

echo "Starting Storage Service…"

if [ -n "${LOG_DIR}" ]; then
  mkdir -p "${LOG_DIR}"
  chown -R appuser:appgroup "${LOG_DIR}"
fi

echo "Ensure storage directory exists at ${STORAGE_PATH}"
mkdir -p "/app/${STORAGE_PATH#./}"
chown -R appuser:appgroup "/app/${STORAGE_PATH#./}"

exec su -c "uvicorn app.main:app --host 0.0.0.0 --port ${EXPOSE_PORT} --reload" appuser