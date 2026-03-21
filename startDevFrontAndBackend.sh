#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
ENV_FILE="$ROOT/.env.dev"

if [ ! -f "$ENV_FILE" ]; then
  echo ".env.dev not found at $ENV_FILE"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required env var: $name (set it in .env.dev)" >&2
    exit 1
  fi
}

require_var "CONDA_ENV"
require_var "BACKEND_HOST"
require_var "BACKEND_PORT"
require_var "FRONTEND_HOST"
require_var "FRONTEND_PORT"

require_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
}

BACKEND_ENTRY="$BACKEND_DIR/backend.py"
FRONTEND_PACKAGE="$FRONTEND_DIR/package.json"
FRONTEND_HTML="$FRONTEND_DIR/index.html"
FRONTEND_ENTRY="$FRONTEND_DIR/src/main.tsx"

require_file "$BACKEND_ENTRY"
require_file "$FRONTEND_PACKAGE"
require_file "$FRONTEND_HTML"
require_file "$FRONTEND_ENTRY"

if [ "${CONDA_DEFAULT_ENV:-}" != "$CONDA_ENV" ]; then
  if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    eval "$(conda shell.bash hook)"
    conda activate "$CONDA_ENV"
  else
    echo "Warning: conda not found; expected env '$CONDA_ENV'." >&2
  fi
fi

echo "Stopping any existing dev processes on ports ${BACKEND_PORT} (backend) and ${FRONTEND_PORT} (frontend)..."
(
  pids="$(lsof -ti tcp:"$BACKEND_PORT" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Killing backend pids: $pids"
    kill $pids 2>/dev/null || true
  fi
  pids="$(lsof -ti tcp:"$FRONTEND_PORT" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Killing frontend pids: $pids"
    kill $pids 2>/dev/null || true
  fi
)

# Track which processes we start
BACK_PID=""
FRONT_PID=""

echo "Starting Flask backend (dev) on http://${BACKEND_HOST}:${BACKEND_PORT} ..."
(
  cd "$BACKEND_DIR"
  BACKEND_HOST="${BACKEND_HOST}" BACKEND_PORT="${BACKEND_PORT}" python backend.py
) &
BACK_PID=$!

echo "Starting Vite dev server (dev env) on http://${FRONTEND_HOST}:${FRONTEND_PORT} ..."
(
  cd "$FRONTEND_DIR"
  FRONTEND_HOST="${FRONTEND_HOST}" FRONTEND_PORT="${FRONTEND_PORT}" npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
) &
FRONT_PID=$!

cleanup() {
  echo "Stopping dev processes..."
  [ -n "$BACK_PID" ] && kill "$BACK_PID" 2>/dev/null || true
  [ -n "$FRONT_PID" ] && kill "$FRONT_PID" 2>/dev/null || true
}
trap cleanup INT TERM

[ -n "$BACK_PID" ] && wait "$BACK_PID"
[ -n "$FRONT_PID" ] && wait "$FRONT_PID"
