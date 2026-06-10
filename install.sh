#!/usr/bin/env bash
# Install openspec-agile-workflow into a target project.
#
# Usage:
#   ./install.sh /path/to/their-project
#   ./install.sh .                    # install into current directory
#
# Prerequisites:
#   npm install -g @fission-ai/openspec
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"

echo "Installing openspec-agile-workflow into: $TARGET"

if ! command -v openspec >/dev/null 2>&1; then
  echo "Error: openspec CLI not found. Install with: npm install -g @fission-ai/openspec"
  exit 1
fi

# OpenSpec skeleton (once per project)
if [[ ! -d "$TARGET/openspec" ]]; then
  echo "Running openspec init --tools cursor ..."
  (cd "$TARGET" && openspec init --tools cursor --force)
else
  echo "openspec/ already exists — skipping init"
fi

# Schema
SCHEMA_SRC="$SCRIPT_DIR/schemas/openspec-agile-workflow"
SCHEMA_DEST="$TARGET/openspec/schemas/openspec-agile-workflow"
mkdir -p "$(dirname "$SCHEMA_DEST")"
rm -rf "$SCHEMA_DEST"
cp -a "$SCHEMA_SRC" "$SCHEMA_DEST"
echo "Installed schema → openspec/schemas/openspec-agile-workflow/"

# Project config (always set schema to openspec-agile-workflow)
CONFIG_EXAMPLE="$SCRIPT_DIR/config.yaml.example"
CONFIG_DEST="$TARGET/openspec/config.yaml"
cp "$CONFIG_EXAMPLE" "$CONFIG_DEST"
echo "Installed config → openspec/config.yaml"

# Custom Cursor commands and skills (must be last — overwrites stock OpenSpec commands)
CURSOR="$SCRIPT_DIR/tooling/cursor"
if [[ -d "$CURSOR/commands" ]]; then
  mkdir -p "$TARGET/.cursor/commands"
  cp -a "$CURSOR/commands/." "$TARGET/.cursor/commands/"
  echo "Installed .cursor/commands/ (opsx-new, opsx-continue, opsx-apply, ...)"
fi
if [[ -d "$CURSOR/skills" ]]; then
  mkdir -p "$TARGET/.cursor/skills"
  cp -a "$CURSOR/skills/." "$TARGET/.cursor/skills/"
  echo "Installed .cursor/skills/"
fi

echo "Validating schema ..."
(cd "$TARGET" && openspec schema validate openspec-agile-workflow)

echo ""
echo "Installation complete."
echo "  1. Restart Cursor"
echo "  2. Start a change: /opsx-new CM-XXX"
echo "  3. Continue: /opsx-continue → /opsx-apply → /opsx-archive"
echo ""
echo "Note: running 'openspec update' overwrites .cursor/ with stock commands."
echo "      Re-run this install.sh to restore the agile-workflow commands."
