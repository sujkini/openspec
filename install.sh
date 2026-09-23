#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DASHBOARD=true
INSTALL_CODEX=false

usage() {
  cat <<EOF
Usage: $0 [--codex] [--no-dashboard] <target-directory>

Installs OpenSpec workflow into the specified project directory:
  1. Installs the OpenSpec CLI (npm)
  2. Runs 'openspec init' in the target directory
  3. Copies openspec/, .cursor/, .codex/, .codex-commands-reference/, eval-generation/, scripts/, and dashboard/ into the target
  4. Installs telemetry Python dependencies (pyyaml, tiktoken)
  5. Installs dashboard Python + Node dependencies (if dashboard enabled)
  6. Updates .gitignore
  7. (--codex) Installs Codex slash commands globally to ~/.codex/prompts/

Options:
  --codex          Also install Codex slash commands globally (runs scripts/install-codex-commands.sh)
  --no-dashboard   Skip copying and installing the observability dashboard

One-liner install (recommended):
  curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- /path/to/project
  curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- --codex /path/to/project
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codex)
      INSTALL_CODEX=true
      shift
      ;;
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
openspec init --tools cursor || true

echo "==> Copying openspec/ into $TARGET_DIR..."
cp -r "$SCRIPT_DIR/openspec" "$TARGET_DIR/"

echo "==> Copying .cursor/ into $TARGET_DIR..."
cp -r "$SCRIPT_DIR/.cursor" "$TARGET_DIR/"

echo "==> Copying .codex/ into $TARGET_DIR..."
if [ -d "$SCRIPT_DIR/.codex" ]; then
  cp -r "$SCRIPT_DIR/.codex" "$TARGET_DIR/"
else
  echo "    Warning: .codex/ not found in source, skipping"
fi

echo "==> Copying .codex-commands-reference/ into $TARGET_DIR..."
if [ -d "$SCRIPT_DIR/.codex-commands-reference" ]; then
  cp -r "$SCRIPT_DIR/.codex-commands-reference" "$TARGET_DIR/"
else
  echo "    Warning: .codex-commands-reference/ not found in source, skipping"
fi

echo "==> Copying scripts/ into $TARGET_DIR..."
if [ -d "$SCRIPT_DIR/scripts" ]; then
  cp -r "$SCRIPT_DIR/scripts" "$TARGET_DIR/"
else
  echo "    Warning: scripts/ not found in source, skipping"
fi

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

# ─── Codex commands ───

if [ "$INSTALL_CODEX" = true ]; then
  CODEX_INSTALLER="$TARGET_DIR/scripts/install-codex-commands.sh"
  if [ -f "$CODEX_INSTALLER" ]; then
    echo "==> Installing Codex slash commands globally..."
    bash "$CODEX_INSTALLER" && \
      echo "    Codex commands installed to ~/.codex/prompts/" || \
      echo "    Warning: Codex command install failed. Run manually: ./scripts/install-codex-commands.sh"
  else
    echo "    Warning: scripts/install-codex-commands.sh not found, skipping Codex commands"
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
echo "======================================================================"
echo "You are about to interact with a Red Hat AI agent. This agent uses AI "
echo "technology to assist you by responding to queries, generating content,"
echo "or performing tasks. By proceeding, you acknowledge that all AI agent "
echo "outputs are intended for internal use only and must be reviewed prior "
echo "to use."
echo "======================================================================"
echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Place agents.md at your repo root     — define your operator's architecture & agent routing"
echo "  2. Add docs to harness-evals/harness-docs/ — operator documentation for constitution generation"
echo "  3. Run /opsx-constitute                   — generates harness-evals/constitution.md from harness-docs"
if [ "$INSTALL_CODEX" = true ]; then
  echo "  4. Restart Codex/VS Code to pick up the new commands"
else
  echo "  4. For Cursor:  Restart Cursor so slash commands load from .cursor/commands/"
  echo "     For Codex:   Re-run with --codex flag, or: ./scripts/install-codex-commands.sh && restart Codex"
fi
echo "  5. Run /opsx-new <JIRA-KEY> to start your first change"
if [ "$INSTALL_DASHBOARD" = true ]; then
  echo "  5. (Optional) Start the dashboard:  cd $TARGET_DIR && ./dashboard/start.sh"
fi
echo ""
echo "Telemetry:"
echo "  Events are written to openspec/changes/<change>/telemetry/events.jsonl"
echo "  Metrics report: openspec/changes/<change>/telemetry/metrics-report.json"
echo "  Manual report:  python -m openspec.telemetry.auto report --change <name>"
echo ""
echo "Feedback:"
echo "  After completing a change, run /opsx-archive to capture your feedback"
echo "  and time savings. This is mandatory for compliance (MON-01)."
echo "  At the end of archive, also submit the external agent feedback form:"
echo "  https://docs.google.com/spreadsheets/d/1lBhSpvjtceexzHGc-dF37F6ho2y4msUnXm5hg52gMus/edit?usp=sharing"
echo ""
