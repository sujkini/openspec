#!/usr/bin/env bash
# One-liner installer for OpenSpec.
#
# Cursor:  curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- /path/to/project
# Codex:   curl -fsSL https://raw.githubusercontent.com/sujkini/openspec/main/bootstrap.sh | bash -s -- --codex /path/to/project
#
# All flags are forwarded to install.sh (e.g. --no-dashboard, --codex).

set -euo pipefail

REPO_URL="https://github.com/sujkini/openspec.git"
BRANCH="main"
CLONE_DIR="$(mktemp -d)"

trap 'rm -rf "$CLONE_DIR"' EXIT

echo "==> Downloading OpenSpec from $REPO_URL ($BRANCH)..."
git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$CLONE_DIR" 2>/dev/null

echo "==> Running installer..."
bash "$CLONE_DIR/install.sh" "$@"
