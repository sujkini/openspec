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

# Eval pipeline + retrospective baseline (for /eval-loop)
EVALS_SRC="$SCRIPT_DIR/evals"
EVALS_DEST="$TARGET/evals"
if [[ -d "$EVALS_SRC" ]]; then
  mkdir -p "$EVALS_DEST"
  if [[ -d "$EVALS_DEST/baseline" ]] || [[ -f "$EVALS_DEST/round-state.yaml" ]]; then
    echo "evals/ exists — updating workflow files (preserving round-state.yaml and baseline/rounds/ when present)"
    for item in inputs epic-bug-analysis eval-generation stages outputs pipeline.yaml README.md refined-templates; do
      cp -a "$EVALS_SRC/$item" "$EVALS_DEST/"
    done
    [[ ! -f "$EVALS_DEST/round-state.yaml" ]] && cp "$EVALS_SRC/round-state.yaml" "$EVALS_DEST/"
  else
    cp -a "$EVALS_SRC" "$EVALS_DEST"
    echo "Installed evals/ → evals/"
  fi

  # Retrospective baseline (eval-loop history) — not used by /opsx-continue forward gate
  mkdir -p "$EVALS_DEST/baseline"
  cp -a "$EVALS_SRC/baseline/evals" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/evals-registry.yaml" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/agents.md" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/README.md" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/refinement-changelog.md" "$EVALS_DEST/baseline/"
  if [[ ! -d "$EVALS_DEST/baseline/rounds" ]] || [[ -z "$(find "$EVALS_DEST/baseline/rounds" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    mkdir -p "$EVALS_DEST/baseline/rounds"
    cp -a "$EVALS_SRC/baseline/rounds/." "$EVALS_DEST/baseline/rounds/" 2>/dev/null || true
  fi
  echo "Installed eval-loop baseline → evals/baseline/"
fi

STAGE_EVAL_COUNT="$(find "$SCHEMA_DEST/evals" -maxdepth 1 -name '*_eval.yaml' 2>/dev/null | wc -l | tr -d ' ')"
echo "Stage evals ship with schema → openspec/schemas/openspec-agile-workflow/evals/ (${STAGE_EVAL_COUNT} files)"

echo "Validating schema ..."
(cd "$TARGET" && openspec schema validate openspec-agile-workflow)

echo ""
echo "Installation complete."
echo "  1. Restart Cursor"
echo "  2. Start a change: /opsx-new CM-XXX"
echo "  3. Continue: /opsx-continue (eval gate per artifact) → /opsx-apply → /opsx-archive"
echo "  4. Eval loop: paste feature bundle into evals/inputs/ → /eval-loop"
echo ""
echo "Note: running 'openspec update' overwrites .cursor/ with stock commands."
echo "      Re-run this install.sh to restore the agile-workflow commands."
