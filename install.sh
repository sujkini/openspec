#!/usr/bin/env bash
# Install openspec-agile-workflow into a target project.
#
# Installs everything required to run the forward workflow (/opsx-new … /opsx-apply):
#   openspec/config.yaml
#   openspec/schemas/openspec-agile-workflow/  (schema, templates, evals, stage-gate, agents.md)
#   openspec/changes/                        (created if missing)
#   .cursor/commands/                        (all files from tooling/cursor/commands/)
#   .cursor/skills/                          (all files from tooling/cursor/skills/)
#   .cursor/e2e-test-generator/              (OAPE e2e fixtures for /oape:e2e-generate)
#   evals/                                   (optional /eval-loop retrospective pipeline)
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

mkdir -p "$TARGET/openspec/changes"

# Schema package (schema.yaml, templates/, evals/, stage-gate/, agents.md)
SCHEMA_SRC="$SCRIPT_DIR/schemas/openspec-agile-workflow"
SCHEMA_DEST="$TARGET/openspec/schemas/openspec-agile-workflow"
AGENTS_SRC="$SCRIPT_DIR/agents.md"

if [[ ! -d "$SCHEMA_SRC" ]]; then
  echo "Error: schema not found at $SCHEMA_SRC"
  exit 1
fi

# Keep agents.md inside the schema package (schema agents_md → {schema_root}/agents.md)
if [[ -f "$AGENTS_SRC" ]]; then
  cp "$AGENTS_SRC" "$SCHEMA_SRC/agents.md"
else
  echo "Warning: agents.md not found at $AGENTS_SRC — schema will ship without agents.md"
fi

mkdir -p "$(dirname "$SCHEMA_DEST")"
rm -rf "$SCHEMA_DEST"
cp -a "$SCHEMA_SRC" "$SCHEMA_DEST"
echo "Installed schema → openspec/schemas/openspec-agile-workflow/"
if [[ -f "$SCHEMA_DEST/agents.md" ]]; then
  echo "  includes agents.md (execution agent routing)"
fi

# Project config (selects openspec-agile-workflow schema + artifact rules)
CONFIG_EXAMPLE="$SCRIPT_DIR/config.yaml.example"
CONFIG_DEST="$TARGET/openspec/config.yaml"
if [[ ! -f "$CONFIG_EXAMPLE" ]]; then
  echo "Error: config.yaml.example not found at $CONFIG_EXAMPLE"
  exit 1
fi
cp "$CONFIG_EXAMPLE" "$CONFIG_DEST"
echo "Installed config → openspec/config.yaml"

# Cursor workflow commands + skills (must be last — overwrites stock OpenSpec commands)
CURSOR="$SCRIPT_DIR/tooling/cursor"
if [[ ! -d "$CURSOR/commands" ]]; then
  echo "Error: tooling/cursor/commands not found at $CURSOR/commands"
  exit 1
fi
mkdir -p "$TARGET/.cursor/commands"
cp -a "$CURSOR/commands/." "$TARGET/.cursor/commands/"
CMD_COUNT="$(find "$TARGET/.cursor/commands" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
echo "Installed .cursor/commands/ (${CMD_COUNT} files from tooling/cursor/commands/)"

if [[ -d "$CURSOR/skills" ]]; then
  mkdir -p "$TARGET/.cursor/skills"
  cp -a "$CURSOR/skills/." "$TARGET/.cursor/skills/"
  SKILL_COUNT="$(find "$TARGET/.cursor/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
  echo "Installed .cursor/skills/ (${SKILL_COUNT} skills from tooling/cursor/skills/)"
else
  echo "Warning: tooling/cursor/skills not found — skipping skills"
fi

if [[ -d "$CURSOR/e2e-test-generator" ]]; then
  mkdir -p "$TARGET/.cursor/e2e-test-generator"
  cp -a "$CURSOR/e2e-test-generator/." "$TARGET/.cursor/e2e-test-generator/"
  echo "Installed .cursor/e2e-test-generator/ (OAPE e2e fixtures for /oape:e2e-generate)"
fi

# Eval pipeline + retrospective baseline (for /eval-loop — not required for /opsx-continue)
EVALS_SRC="$SCRIPT_DIR/evals"
EVALS_DEST="$TARGET/evals"
if [[ -d "$EVALS_SRC" ]]; then
  mkdir -p "$EVALS_DEST"
  if [[ -d "$EVALS_DEST/baseline" ]] || [[ -f "$EVALS_DEST/round-state.yaml" ]]; then
    echo "evals/ exists — updating workflow files (preserving round-state.yaml and baseline/rounds/ when present)"
    for item in inputs epic-bug-analysis eval-generation stages outputs pipeline.yaml README.md refined-templates; do
      [[ -e "$EVALS_SRC/$item" ]] && cp -a "$EVALS_SRC/$item" "$EVALS_DEST/"
    done
    [[ ! -f "$EVALS_DEST/round-state.yaml" ]] && cp "$EVALS_SRC/round-state.yaml" "$EVALS_DEST/"
  else
    cp -a "$EVALS_SRC" "$EVALS_DEST"
    echo "Installed evals/ → evals/"
  fi

  mkdir -p "$EVALS_DEST/baseline"
  cp -a "$EVALS_SRC/baseline/evals" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/evals-registry.yaml" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/routing-learnings.md" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/README.md" "$EVALS_DEST/baseline/"
  cp "$EVALS_SRC/baseline/refinement-changelog.md" "$EVALS_DEST/baseline/"
  if [[ ! -d "$EVALS_DEST/baseline/rounds" ]] || [[ -z "$(find "$EVALS_DEST/baseline/rounds" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    mkdir -p "$EVALS_DEST/baseline/rounds"
    cp -a "$EVALS_SRC/baseline/rounds/." "$EVALS_DEST/baseline/rounds/" 2>/dev/null || true
  fi
  echo "Installed eval-loop baseline → evals/baseline/"
fi

STAGE_EVAL_COUNT="$(find "$SCHEMA_DEST/evals" -maxdepth 1 -name '*_eval.yaml' 2>/dev/null | wc -l | tr -d ' ')"
echo "Stage evals in schema package: ${STAGE_EVAL_COUNT} files"

echo "Validating schema ..."
(cd "$TARGET" && openspec schema validate openspec-agile-workflow)

echo ""
echo "Installation complete."
echo ""
echo "openspec/ (forward workflow):"
echo "  openspec/config.yaml"
echo "  openspec/schemas/openspec-agile-workflow/  (schema, templates, evals, stage-gate, agents.md)"
echo "  openspec/changes/"
echo ""
echo "Cursor:"
echo "  .cursor/commands/  — opsx-new, opsx-continue, opsx-apply, opsx-archive, OAPE commands, eval-loop"
echo "  .cursor/skills/    — openspec-* skills + OAPE effective-go, e2e-test-generator"
echo "  .cursor/e2e-test-generator/  — e2e fixtures for /oape:e2e-generate"
echo ""
echo "Next steps:"
echo "  1. Restart Cursor"
echo "  2. /opsx-new CM-XXX"
echo "  3. /opsx-continue (eval gate per artifact) → /opsx-apply → /opsx-archive"
echo "  4. Optional: /eval-loop (requires evals/ at project root)"
echo ""
echo "Note: 'openspec update' overwrites .cursor/ with stock commands."
echo "      Re-run this install.sh to restore the agile-workflow commands."
