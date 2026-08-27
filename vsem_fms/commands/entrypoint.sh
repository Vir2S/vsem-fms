#!/bin/bash
set -euo pipefail

STORAGE_PATH="${STORAGE_PATH:-./storage}"
LOG_DIR="${LOG_DIR:-./logs}"
SERVER_HOST="${SERVER_HOST:-0.0.0.0}"
SERVER_PORT="${SERVER_PORT:-5000}"

resolve_app_path() {
  case "$1" in
    /*) printf '%s' "$1" ;;
    *) printf '/app/%s' "${1#./}" ;;
  esac
}

STORAGE_DIR="$(resolve_app_path "$STORAGE_PATH")"
LOG_PATH="$(resolve_app_path "$LOG_DIR")"

mkdir -p "$STORAGE_DIR" "$LOG_PATH"
chown -R appuser:appgroup "$STORAGE_DIR" "$LOG_PATH"

export STORAGE_PATH="$STORAGE_DIR"
export LOG_DIR="$LOG_PATH"
export SERVER_HOST SERVER_PORT

exec su -s /bin/sh appuser -c \
  'exec uvicorn vsem_fms.app.main:app --host "$SERVER_HOST" --port "$SERVER_PORT"'
