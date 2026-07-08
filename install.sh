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
  4. Installs telemetry Python dependencies (pyyaml, tiktoken)
  5. Updates .gitignore

Prerequisites:
  rm -rf /tmp/openspec-workflow
  git clone -b openspec-backend https://github.com/sujkini/openspec.git /tmp/openspec-workflow

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

echo "==> Installing telemetry Python dependencies..."
PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -n "$PYTHON_BIN" ] && [ -f "$TARGET_DIR/openspec/telemetry/requirements.txt" ]; then
  "$PYTHON_BIN" -m pip install -r "$TARGET_DIR/openspec/telemetry/requirements.txt" -q && \
    echo "    Python dependencies installed (pyyaml, tiktoken)." || \
    echo "    Warning: pip install failed. Run manually: pip install -r openspec/telemetry/requirements.txt"
else
  echo "    Warning: python3 not found. Install manually: pip install pyyaml tiktoken"
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

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit openspec/inputs/agents.md      — define your operator's architecture & agent routing"
echo "  2. Edit openspec/inputs/constitution.md — define coding guardrails & CI gates"
echo "  3. Restart Cursor so slash commands load from .cursor/commands/"
echo "  4. Run /opsx-new <JIRA-KEY> to start your first change"
echo ""
echo "Telemetry:"
echo "  Events are written to openspec/changes/<change>/telemetry/events.jsonl"
echo "  Metrics report: openspec/changes/<change>/telemetry/metrics-report.json"
echo "  Manual report:  python -m openspec.telemetry.auto report --change <name>"
echo ""
