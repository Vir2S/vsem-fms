#!/bin/bash
set -euo pipefail

echo "Starting VSEM FMS…"

STORAGE_PATH="${STORAGE_PATH:-./storage}"
LOG_DIR="${LOG_DIR:-./logs}"
SERVER_PORT="${SERVER_PORT:-5000}"

mkdir -p "${STORAGE_PATH}" "${LOG_DIR}"
chown -R appuser:appgroup "${STORAGE_PATH}" "${LOG_DIR}"

exec su -s /bin/sh appuser -c \
  "uvicorn vsem_fms.app.main:app --host 0.0.0.0 --port ${SERVER_PORT}"
