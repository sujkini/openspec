#!/usr/bin/env bash
# run-local.sh — Local CI monitor entry point for OpenSpec (/opsx-ci-monitor).
#
# Sources openspec/config.yaml phase flags and runs pr-agent/entrypoint.sh,
# then copies report artifacts into the OpenSpec change directory.
#
# Usage:
#   run-local.sh --pr-url <URL> [--change <name>] [--config openspec/config.yaml]
#                  [--dry-run] [--monitor-only] [--review]
#
# Environment:
#   GH_TOKEN, RUNNER_TEMP (optional)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CI_MONITOR_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CI_MONITOR_ROOT/../.." && pwd)"

PR_URL=""
CHANGE_NAME=""
CONFIG_FILE="${REPO_ROOT}/openspec/config.yaml"
DRY_RUN=false
CLI_MONITOR_ONLY=""
CLI_REVIEW=""

usage() {
  echo "Usage: run-local.sh --pr-url <URL> [--change <name>] [--config <path>]"
  echo "                    [--dry-run] [--monitor-only] [--review]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr-url)       PR_URL="$2"; shift 2 ;;
    --change)       CHANGE_NAME="$2"; shift 2 ;;
    --config)       CONFIG_FILE="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=true; shift ;;
    --monitor-only) CLI_MONITOR_ONLY=true; shift ;;
    --review)       CLI_REVIEW=true; shift ;;
    -h|--help)      usage ;;
    *)              echo "Unknown argument: $1" >&2; usage ;;
  esac
done

if [[ -z "$PR_URL" ]]; then
  echo "ERROR: --pr-url is required" >&2
  usage
fi

if [[ ! "$PR_URL" =~ ^https://github.com/[^/]+/[^/]+/pull/[0-9]+$ ]]; then
  echo "ERROR: Invalid PR URL format: ${PR_URL}" >&2
  exit 1
fi

OWNER=$(echo "$PR_URL" | sed 's|https://github.com/||;s|/pull/.*||' | cut -d/ -f1)
REPO=$(echo "$PR_URL" | sed 's|https://github.com/||;s|/pull/.*||' | cut -d/ -f2)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')

TEAM_REPOS_CSV="${CI_MONITOR_ROOT}/config/team-repos.csv"
if [[ -f "$TEAM_REPOS_CSV" ]] && ! grep -q "github.com/${OWNER}/${REPO}" "$TEAM_REPOS_CSV"; then
  echo "WARN: ${OWNER}/${REPO} is not in ${TEAM_REPOS_CSV} — continuing anyway"
fi

# Load phase flags from openspec config
# shellcheck source=ci-monitor/load-openspec-config.sh
source "${CI_MONITOR_ROOT}/scripts/ci-monitor/load-openspec-config.sh" "$CONFIG_FILE"

if [[ "$CI_MONITOR_ENABLED" != "true" ]]; then
  echo "[run-local] ci_monitor.enabled=false — nothing to do"
  exit 0
fi

if [[ "$CI_MONITOR_RUNTIME" == "prow" ]]; then
  echo "[run-local] ci_monitor.runtime=prow — use Prow job oape-ci-monitor or set runtime to local|both"
  echo "[run-local] Template: openspec/ci-monitor/docs/prow-ci-operator-config.yaml"
  exit 1
fi

export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-$(gh auth token 2>/dev/null || echo '')}}"
if [[ -z "$GH_TOKEN" ]]; then
  echo "ERROR: GH_TOKEN not set and gh auth token unavailable" >&2
  exit 1
fi

export RUNNER_TEMP="${RUNNER_TEMP:-$(mktemp -d)}"
export OAPE_ROOT="$CI_MONITOR_ROOT"

ENTRYPOINT_ARGS=(--mode on-demand --pr-url "$PR_URL")

if [[ "$DRY_RUN" == "true" ]]; then
  ENTRYPOINT_ARGS+=(--dry-run)
fi

if [[ -n "$CLI_MONITOR_ONLY" ]]; then
  ENTRYPOINT_ARGS+=(--monitor-only)
elif [[ "$MONITOR_ONLY" == "true" ]]; then
  ENTRYPOINT_ARGS+=(--monitor-only)
fi

if [[ -n "$CLI_REVIEW" ]]; then
  ENTRYPOINT_ARGS+=(--review)
elif [[ "$REVIEW_HANDLER_ENABLED" == "true" && "$MONITOR_ONLY" != "true" ]]; then
  ENTRYPOINT_ARGS+=(--review)
fi

echo "============================================"
echo "  OpenSpec CI Monitor (local)"
echo "  PR: ${PR_URL}"
echo "  Runtime: ${CI_MONITOR_RUNTIME}"
echo "  Phase: ${PHASE}"
echo "  Args: ${ENTRYPOINT_ARGS[*]}"
echo "  RUNNER_TEMP: ${RUNNER_TEMP}"
echo "============================================"

"${CI_MONITOR_ROOT}/scripts/pr-agent/entrypoint.sh" "${ENTRYPOINT_ARGS[@]}"

REPORT_FILE="${RUNNER_TEMP}/pr-agent-report-${OWNER}-${REPO}-${PR_NUMBER}.md"
STATUS_FILE="${RUNNER_TEMP}/ci-status-${OWNER}-${REPO}-${PR_NUMBER}.json"

if [[ -n "$CHANGE_NAME" ]]; then
  IMPL_DIR="${REPO_ROOT}/openspec/changes/${CHANGE_NAME}/implementation"
  mkdir -p "$IMPL_DIR"

  if [[ -f "$REPORT_FILE" ]]; then
    cp "$REPORT_FILE" "${IMPL_DIR}/ci-monitor-summary.md"
    echo "[run-local] Wrote ${IMPL_DIR}/ci-monitor-summary.md"
  fi

  if [[ -f "$STATUS_FILE" ]]; then
    cp "$STATUS_FILE" "${IMPL_DIR}/ci-monitor-status.json"
    echo "[run-local] Wrote ${IMPL_DIR}/ci-monitor-status.json"
  fi
else
  echo "[run-local] No --change name; artifacts remain in ${RUNNER_TEMP}"
  [[ -f "$REPORT_FILE" ]] && echo "[run-local] Report: ${REPORT_FILE}"
fi

if [[ -f "$REPORT_FILE" ]]; then
  echo ""
  echo "=========================================="
  echo "  CI Monitor Report Summary"
  echo "=========================================="
  head -40 "$REPORT_FILE"
fi

echo ""
echo "[run-local] Done. Re-run after CI updates, or run /opsx-e2e when checks are green."
