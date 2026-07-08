#!/usr/bin/env bash
set -euo pipefail

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DASHBOARD_DIR/.dashboard-pids"

# ── stop mode ──────────────────────────────────────────────────────────────────
stop_dashboard() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "No running dashboard found (missing $PID_FILE)."
    exit 0
  fi
  echo "==> Stopping dashboard processes..."
  while IFS= read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "    Stopped PID $pid"
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  echo "    Dashboard stopped."
  exit 0
}

if [[ "${1:-}" == "--stop" ]]; then
  stop_dashboard
fi

# ── preflight checks ──────────────────────────────────────────────────────────
if [[ ! -f "$DASHBOARD_DIR/config.json" ]]; then
  echo "Error: $DASHBOARD_DIR/config.json not found."
  echo "       Run install.sh first."
  exit 1
fi

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo "Error: Python 3.10+ is required. Install it and try again."
  exit 1
fi
PYTHON="$(command -v python3 || command -v python)"

if ! command -v node &>/dev/null; then
  echo "Error: Node.js 18+ is required. Install it and try again."
  exit 1
fi

CHANGES_DIR="$("$PYTHON" -c "import json; print(json.load(open('$DASHBOARD_DIR/config.json'))['openspec']['changes_dir'])" 2>/dev/null || echo "")"
if [[ -z "$CHANGES_DIR" || "$CHANGES_DIR" == "openspec/changes" ]]; then
  echo "Warning: config.json has default relative changes_dir."
  echo "         Run install.sh <target-dir> to configure absolute paths."
  echo "         Proceeding with relative paths (works if CWD is the operator repo)."
fi

if [[ ! -d "$DASHBOARD_DIR/web/node_modules" ]]; then
  echo "==> Installing frontend dependencies..."
  (cd "$DASHBOARD_DIR/web" && npm install)
fi

if ! "$PYTHON" -c "import fastapi" 2>/dev/null; then
  echo "==> Installing backend dependencies..."
  "$PYTHON" -m pip install -r "$DASHBOARD_DIR/requirements.txt" -q
fi

# ── prepare runtime dirs ──────────────────────────────────────────────────────
mkdir -p "$DASHBOARD_DIR/data"

# ── cleanup on exit ───────────────────────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "==> Shutting down dashboard..."
  [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null && echo "    Backend stopped."
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null && echo "    Frontend stopped."
  rm -f "$PID_FILE"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── start backend (port 8000) ─────────────────────────────────────────────────
echo "==> Starting backend API on http://localhost:8000 ..."
export PYTHONPATH="$DASHBOARD_DIR${PYTHONPATH:+:$PYTHONPATH}"
(cd "$DASHBOARD_DIR" && "$PYTHON" -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

sleep 2

# ── start frontend (port 5173) ────────────────────────────────────────────────
echo "==> Starting frontend UI on http://localhost:5173 ..."
(cd "$DASHBOARD_DIR/web" && npm run dev -- --host 0.0.0.0) &
FRONTEND_PID=$!

# ── write PID file for --stop ─────────────────────────────────────────────────
echo "$BACKEND_PID" > "$PID_FILE"
echo "$FRONTEND_PID" >> "$PID_FILE"

echo ""
echo "============================================"
echo "  Dashboard is running!"
echo ""
echo "  UI:      http://localhost:5173"
echo "  API:     http://localhost:8000"
echo "  API doc: http://localhost:8000/docs"
echo ""
echo "  Stop:    $0 --stop"
echo "           or Ctrl+C"
echo "============================================"
echo ""

# ── wait for either process to exit ───────────────────────────────────────────
wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
cleanup
