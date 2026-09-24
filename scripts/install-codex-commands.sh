#!/bin/bash
# Install OpenSpec Codex commands and skills — single-source from .cursor/
# Usage: ./scripts/install-codex-commands.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMMANDS_SOURCE="$PROJECT_ROOT/.cursor/commands"
SKILLS_SOURCE="$PROJECT_ROOT/.cursor/skills"
COMMANDS_DEST="$HOME/.codex/prompts"
SKILLS_DEST="$PROJECT_ROOT/.codex/skills"

echo "Installing OpenSpec Codex commands (single-source from .cursor/)..."

# --- Commands ---
mkdir -p "$COMMANDS_DEST"

if [ -d "$COMMANDS_SOURCE" ]; then
    cp "$COMMANDS_SOURCE"/*.md "$COMMANDS_DEST/" || {
        echo "Error: Could not copy command files"
        exit 1
    }
    CMD_COUNT=$(ls "$COMMANDS_SOURCE"/*.md 2>/dev/null | wc -l)
    echo "  Installed $CMD_COUNT commands to $COMMANDS_DEST"
else
    echo "Error: Source directory not found: $COMMANDS_SOURCE"
    exit 1
fi

# --- Skills ---
if [ -d "$SKILLS_SOURCE" ]; then
    mkdir -p "$SKILLS_DEST"
    cp -r "$SKILLS_SOURCE"/* "$SKILLS_DEST/" || {
        echo "Warning: Could not copy skills"
    }
    SKILL_COUNT=$(find "$SKILLS_SOURCE" -name "SKILL.md" 2>/dev/null | wc -l)
    echo "  Installed $SKILL_COUNT skills to $SKILLS_DEST"
else
    echo "  Warning: No skills found at $SKILLS_SOURCE"
fi

echo "  Restart Codex to pick up the new commands"
