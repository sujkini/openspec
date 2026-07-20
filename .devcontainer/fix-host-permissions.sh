#!/usr/bin/env bash
# Runs on the HOST (not inside the dev container).
# Fixes ownership, SELinux context, and ACLs for bind-mounted workspace paths.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(id -un)"
GROUP_NAME="$(id -gn)"
NEEDS_SUDO=false

needs_ownership_fix() {
  find "$REPO_ROOT" \( ! -user "$USER_NAME" -o ! -group "$GROUP_NAME" \) -print -quit 2>/dev/null | grep -q .
}

fix_ownership() {
  if needs_ownership_fix; then
    echo "==> Fixing ownership under $REPO_ROOT"
    sudo chown -R "$USER_NAME:$GROUP_NAME" "$REPO_ROOT"
    NEEDS_SUDO=true
  fi
}

fix_selinux() {
  if command -v getenforce &>/dev/null && [ "$(getenforce)" = "Enforcing" ] \
     && command -v chcon &>/dev/null; then
    if ! ls -dZ "$REPO_ROOT" 2>/dev/null | grep -q 'container_file_t'; then
      echo "==> Fixing SELinux context (container_file_t)"
      sudo chcon -R -t container_file_t "$REPO_ROOT"
      NEEDS_SUDO=true
    fi
  fi
}

fix_acls() {
  if command -v setfacl &>/dev/null && command -v getfacl &>/dev/null; then
    if getfacl -s "$REPO_ROOT" 2>/dev/null | grep -qE '^user:|^group:|^mask:'; then
      echo "==> Clearing restrictive ACLs"
      sudo setfacl -R -b "$REPO_ROOT"
      NEEDS_SUDO=true
    fi
  fi
}

fix_ownership
fix_selinux
fix_acls

if [ "$NEEDS_SUDO" = false ]; then
  echo "==> Permissions OK — no changes needed"
fi
