#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DASHBOARD=true

usage() {
  cat <<EOF
Usage: $0 [--no-dashboard] <target-directory>

Installs OpenSpec workflow into the specified project directory:
  1. Installs the OpenSpec CLI (npm)
  2. Runs 'openspec init' in the target directory
  3. Copies openspec/, .cursor/, eval-generation/, and dashboard/ into the target
  4. Installs telemetry Python dependencies (pyyaml, tiktoken)
  5. Installs dashboard Python + Node dependencies (if dashboard enabled)
  6. Updates .gitignore

Options:
  --no-dashboard   Skip copying and installing the observability dashboard

Prerequisites:
  git clone https://github.com/sujkini/openspec.git /tmp/openspec-workflow

Then run:
  /tmp/openspec-workflow/install.sh /path/to/your-project
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-dashboard)
      INSTALL_DASHBOARD=false
      shift
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo "Unknown option: $1"
      usage
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 1 ]]; then
  usage
fi

TARGET_DIR="$(realpath "$1")"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: target directory '$TARGET_DIR' does not exist."
  exit 1
fi

echo "==> Installing OpenSpec CLI..."
if command -v openspec &>/dev/null; then
  echo "    openspec CLI already installed: $(openspec --version 2>/dev/null || echo 'unknown version')"
else
  npm install -g @fission-ai/openspec
  echo "    openspec CLI installed."
fi

echo "==> Running 'openspec init' in $TARGET_DIR..."
cd "$TARGET_DIR"
openspec init || true

echo "==> Copying openspec/ into $TARGET_DIR..."
cp -r "$SCRIPT_DIR/openspec" "$TARGET_DIR/"

echo "==> Copying .cursor/ into $TARGET_DIR..."
cp -r "$SCRIPT_DIR/.cursor" "$TARGET_DIR/"

echo "==> Copying eval-generation/ into $TARGET_DIR..."
cp -r "$SCRIPT_DIR/eval-generation" "$TARGET_DIR/"

echo "==> Installing telemetry Python dependencies..."
PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -n "$PYTHON_BIN" ] && [ -f "$TARGET_DIR/openspec/telemetry/requirements.txt" ]; then
  "$PYTHON_BIN" -m pip install -r "$TARGET_DIR/openspec/telemetry/requirements.txt" -q && \
    echo "    Python dependencies installed (pyyaml, tiktoken)." || \
    echo "    Warning: pip install failed. Run manually: pip install -r openspec/telemetry/requirements.txt"
else
  echo "    Warning: python3 not found. Install manually: pip install pyyaml tiktoken"
fi

# ─── Dashboard ───

if [ "$INSTALL_DASHBOARD" = true ] && [ -d "$SCRIPT_DIR/dashboard" ]; then
  echo "==> Copying dashboard/ into $TARGET_DIR..."
  if command -v rsync &>/dev/null; then
    rsync -a --exclude='.venv' --exclude='data' --exclude='web/node_modules' \
          --exclude='web/dist' --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='web/tsconfig.tsbuildinfo' \
          "$SCRIPT_DIR/dashboard/" "$TARGET_DIR/dashboard/"
  else
    cp -r "$SCRIPT_DIR/dashboard" "$TARGET_DIR/"
  fi

  TARGET_CONFIG="$TARGET_DIR/dashboard/config.json"
  if [ -f "$TARGET_CONFIG" ]; then
    sed -i "s|\"workspace\".*|\"workspace\": \"$TARGET_DIR\",|" "$TARGET_CONFIG"
    echo "    Dashboard config.json workspace set to $TARGET_DIR"
  fi

  echo "==> Installing dashboard Python dependencies..."
  if [ -n "$PYTHON_BIN" ] && [ -f "$TARGET_DIR/dashboard/requirements.txt" ]; then
    "$PYTHON_BIN" -m pip install -r "$TARGET_DIR/dashboard/requirements.txt" -q && \
      echo "    Dashboard Python dependencies installed." || \
      echo "    Warning: pip install failed. Run manually: pip install -r dashboard/requirements.txt"
  fi

  echo "==> Installing dashboard frontend dependencies..."
  if command -v node &>/dev/null && [ -f "$TARGET_DIR/dashboard/web/package.json" ]; then
    (cd "$TARGET_DIR/dashboard/web" && npm install --silent) && \
      echo "    Frontend dependencies installed." || \
      echo "    Warning: npm install failed. Run manually: cd dashboard/web && npm install"
  else
    echo "    Warning: node not found. Install Node.js 18+ then run: cd dashboard/web && npm install"
  fi
else
  if [ "$INSTALL_DASHBOARD" = false ]; then
    echo "==> Skipping dashboard (--no-dashboard)"
  fi
fi

echo "==> Updating .gitignore..."
GITIGNORE="$TARGET_DIR/.gitignore"
touch "$GITIGNORE"

add_if_missing() {
  local entry="$1"
  if ! grep -qxF "$entry" "$GITIGNORE"; then
    echo "$entry" >> "$GITIGNORE"
  fi
}

add_if_missing "# ─── OpenSpec runtime artifacts (never commit) ───"
add_if_missing "eval-generation/output-evals/"
add_if_missing "eval-generation/output-refined-templates/"
add_if_missing "eval-generation/eval-generation-workflow/outputs/"
add_if_missing "eval-generation/eval-generation-workflow/rounds/"
add_if_missing "eval-generation/eval-generation-workflow/template-gaps/"
add_if_missing "eval-generation/eval-generation-workflow/refined-templates/"
add_if_missing "eval-generation/eval-generation-workflow/round-state.yaml"
add_if_missing "openspec/changes/"

if [ "$INSTALL_DASHBOARD" = true ]; then
  add_if_missing "# ─── Dashboard runtime artifacts ───"
  add_if_missing "dashboard/data/"
  add_if_missing "dashboard/.venv/"
  add_if_missing "dashboard/web/node_modules/"
  add_if_missing "dashboard/web/dist/"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit openspec/inputs/agents.md      — define your operator's architecture & agent routing"
echo "  2. Edit openspec/inputs/constitution.md — define coding guardrails & CI gates"
echo "  3. Restart Cursor so slash commands load from .cursor/commands/"
echo "  4. Run /opsx-new <JIRA-KEY> to start your first change"
if [ "$INSTALL_DASHBOARD" = true ]; then
  echo "  5. (Optional) Start the dashboard:  cd $TARGET_DIR && ./dashboard/start.sh"
fi
echo ""
echo "Telemetry:"
echo "  Events are written to openspec/changes/<change>/telemetry/events.jsonl"
echo "  Metrics report: openspec/changes/<change>/telemetry/metrics-report.json"
echo "  Manual report:  python -m openspec.telemetry.auto report --change <name>"
echo ""
