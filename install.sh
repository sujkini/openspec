#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: $0 <target-directory>

Installs OpenSpec workflow into the specified project directory:
  1. Installs the OpenSpec CLI (npm)
  2. Runs 'openspec init' in the target directory
  3. Copies openspec/, .cursor/, and eval-generation/ from this repo into the target
  4. Updates .gitignore

Prerequisites:
  git clone -b openspec-operator-generic https://github.com/sujkini/openspec.git /tmp/openspec-workflow

Then run:
  /tmp/openspec-workflow/install.sh /path/to/your-project
EOF
  exit 1
}

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

echo "==> Configuring dashboard for $TARGET_DIR ..."
DASHBOARD_DIR="$SCRIPT_DIR/dashboard"
DASHBOARD_CONFIG="$DASHBOARD_DIR/config.json"
DB_PATH="$DASHBOARD_DIR/data/dashboard.db"

if [ -f "$DASHBOARD_CONFIG" ]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  if [ -n "$PYTHON_BIN" ]; then
    "$PYTHON_BIN" - "$DASHBOARD_CONFIG" "$TARGET_DIR" "$DB_PATH" <<'PYEOF'
import json, sys
config_path, target_dir, db_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(config_path) as f:
    cfg = json.load(f)
cfg["openspec"]["changes_dir"] = target_dir + "/openspec/changes"
cfg["database"]["url"] = "sqlite+aiosqlite:///" + db_path
cfg["telemetry"]["bus_dir"] = target_dir + "/openspec/changes"
with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PYEOF
    echo "    config.json patched:"
    echo "      changes_dir  = $TARGET_DIR/openspec/changes"
    echo "      database.url = sqlite+aiosqlite:///$DB_PATH"
  else
    echo "    Warning: python3 not found — config.json not patched."
    echo "    Set openspec.changes_dir manually in $DASHBOARD_CONFIG"
  fi
fi

echo "==> Installing dashboard dependencies..."
if [ -n "${PYTHON_BIN:-}" ] && [ -f "$DASHBOARD_DIR/requirements.txt" ]; then
  "$PYTHON_BIN" -m pip install -r "$DASHBOARD_DIR/requirements.txt" -q && \
    echo "    Python dependencies installed." || \
    echo "    Warning: pip install failed. Run manually: pip install -r $DASHBOARD_DIR/requirements.txt"
fi

if command -v npm &>/dev/null && [ -f "$DASHBOARD_DIR/web/package.json" ]; then
  if [ ! -d "$DASHBOARD_DIR/web/node_modules" ]; then
    (cd "$DASHBOARD_DIR/web" && npm install --silent) && \
      echo "    Frontend dependencies installed." || \
      echo "    Warning: npm install failed. Run manually: cd $DASHBOARD_DIR/web && npm install"
  else
    echo "    Frontend dependencies already installed."
  fi
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit openspec/inputs/agents.md      — define your operator's architecture & agent routing"
echo "  2. Edit openspec/inputs/constitution.md — define coding guardrails & CI gates"
echo "  3. Restart Cursor so slash commands load from .cursor/commands/"
echo "  4. (Optional) Start the dashboard:"
echo "       $DASHBOARD_DIR/start.sh"
echo "  5. (Optional) Run /eval-loop to generate quality evals from a completed feature"
echo "  6. Run /opsx-new <JIRA-KEY> to start your first change"
echo ""
