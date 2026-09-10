#!/usr/bin/env bash
# load-openspec-config.sh — Read openspec/config.yaml ci_monitor flags and export env vars.
#
# Usage (source, do not execute):
#   source openspec/ci-monitor/scripts/ci-monitor/load-openspec-config.sh [path/to/openspec/config.yaml]
#
# Exports: CI_MONITOR_RUNTIME, PHASE, MONITOR_ONLY, REVIEW_HANDLER_ENABLED,
#          RETEST_INFRA_FLAKES, MAX_RETESTS_PER_RUN, CI_MONITOR_ENABLED, POST_PR_COMMENT
# Safe defaults when config is missing or ci_monitor section is absent.

set -euo pipefail

CONFIG_FILE="${1:-openspec/config.yaml}"

# Defaults: Phase 3 (analysis + auto-fix + review handler), local runtime
export CI_MONITOR_ENABLED="${CI_MONITOR_ENABLED:-true}"
export CI_MONITOR_RUNTIME="${CI_MONITOR_RUNTIME:-local}"
export PHASE="${PHASE:-3}"
export MONITOR_ONLY="${MONITOR_ONLY:-false}"
export REVIEW_HANDLER_ENABLED="${REVIEW_HANDLER_ENABLED:-true}"
export RETEST_INFRA_FLAKES="${RETEST_INFRA_FLAKES:-false}"
export MAX_RETESTS_PER_RUN="${MAX_RETESTS_PER_RUN:-2}"
export POST_PR_COMMENT="${POST_PR_COMMENT:-true}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[config] No config at ${CONFIG_FILE} — using Phase 3 local defaults"
  return 0 2>/dev/null || exit 0
fi

if ! command -v python3 &>/dev/null; then
  echo "[config] WARN: python3 not found — using Phase 3 defaults" >&2
  return 0 2>/dev/null || exit 0
fi

eval "$(python3 - "$CONFIG_FILE" <<'PY'
import sys

try:
    import yaml
except ImportError:
    print('echo "[config] WARN: PyYAML not installed — using Phase 3 defaults" >&2', file=sys.stderr)
    sys.exit(0)

path = sys.argv[1]
with open(path) as f:
    cfg = yaml.safe_load(f) or {}

cm = cfg.get("ci_monitor") or {}
if not cm.get("enabled", True):
    print('export CI_MONITOR_ENABLED="false"')
    sys.exit(0)

runtime = str(cm.get("runtime", "local")).lower()
if runtime not in ("local", "prow", "both"):
    runtime = "local"

phase = int(cm.get("phase", 3))
monitor_only = bool(cm.get("monitor_only", phase < 2))
auto_fix = bool(cm.get("auto_fix", phase >= 2))
review_handler = bool(cm.get("review_handler", phase >= 3))
retest = bool(cm.get("retest_infra_flakes", False))
max_retests = int(cm.get("max_retests_per_run", 2))
post_pr_comment = bool(cm.get("post_pr_comment", True))

if monitor_only and not auto_fix:
    dispatch_monitor_only = True
else:
    dispatch_monitor_only = not auto_fix

print('export CI_MONITOR_ENABLED="true"')
print(f'export CI_MONITOR_RUNTIME="{runtime}"')
print(f'export PHASE="{phase}"')
print(f'export MONITOR_ONLY="{"true" if dispatch_monitor_only else "false"}"')
print(f'export REVIEW_HANDLER_ENABLED="{"true" if review_handler else "false"}"')
print(f'export RETEST_INFRA_FLAKES="{"true" if retest else "false"}"')
print(f'export MAX_RETESTS_PER_RUN="{max_retests}"')
print(f'export POST_PR_COMMENT="{"true" if post_pr_comment else "false"}"')
PY
)"

echo "[config] Loaded ci_monitor from ${CONFIG_FILE}: runtime=${CI_MONITOR_RUNTIME} PHASE=${PHASE} MONITOR_ONLY=${MONITOR_ONLY} REVIEW_HANDLER=${REVIEW_HANDLER_ENABLED}"
