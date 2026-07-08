#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Resolve workspace: arg > env var > config.json > parent dir
if [ -n "${1:-}" ]; then
  export OPSX_WORKSPACE="$1"
elif [ -n "${OPSX_WORKSPACE:-}" ]; then
  export OPSX_WORKSPACE
elif [ -f "config.json" ]; then
  CFG_WORKSPACE="$(grep '"workspace"' config.json | sed 's/.*: *"\(.*\)".*/\1/' | sed 's/,$//')"
  if [ -n "$CFG_WORKSPACE" ] && [[ "$CFG_WORKSPACE" != *'${'* ]]; then
    export OPSX_WORKSPACE="$CFG_WORKSPACE"
  else
    export OPSX_WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
  fi
else
  export OPSX_WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

echo "==> OpenSpec Observability Dashboard"
echo "    Workspace: $OPSX_WORKSPACE"
echo "    Changes:   $OPSX_WORKSPACE/openspec/changes"
echo ""

if [ ! -d "$OPSX_WORKSPACE/openspec" ]; then
  echo "Warning: $OPSX_WORKSPACE/openspec/ not found. Dashboard may not find pipeline data."
  echo ""
fi

if command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
  echo "==> Docker detected. Starting dashboard with Docker Compose..."
  docker compose up -d --build
  echo ""
  echo "Dashboard running at http://localhost:5173"
  echo "Backend API at http://localhost:8000"
  echo ""
  echo "To stop:  cd $SCRIPT_DIR && docker compose down"
  echo "To logs:  cd $SCRIPT_DIR && docker compose logs -f"
else
  echo "==> Docker not found. Setting up locally..."
  echo ""

  if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required. Install Python 3.10+ and try again."
    exit 1
  fi

  if ! command -v node &>/dev/null; then
    echo "Error: node is required. Install Node.js 18+ and try again."
    exit 1
  fi

  if [ ! -d ".venv" ]; then
    echo "    Creating Python virtual environment..."
    python3 -m venv .venv
  fi

  echo "    Installing Python dependencies..."
  .venv/bin/pip install -q -r requirements.txt

  echo "    Installing frontend dependencies..."
  cd web && npm install && cd ..

  echo ""
  echo "==> Starting dashboard (backend + frontend)..."
  echo "    Backend: http://localhost:8000"
  echo "    Frontend: http://localhost:5173"
  echo ""

  .venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!
  cd web && npm run dev &
  FRONTEND_PID=$!
  cd ..

  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
  wait
fi
