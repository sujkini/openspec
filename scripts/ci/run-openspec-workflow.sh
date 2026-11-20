#!/bin/bash
# Runner for the openspec agile and QE workflows on OpenShift CI.
#
# Drives the OpenAI Codex CLI (`codex exec` + `codex exec resume`) through the
# /opsx-* command prompts bundled in the openspec-agent-worker image, handling
# the interactive approval gates non-interactively and reporting created PRs.
#
# Usage (from a ci-operator step):
#   run-openspec-workflow.sh agile   # or: WORKFLOW=agile run-openspec-workflow.sh
#   run-openspec-workflow.sh qe
#
# Required environment (injected by ci-operator):
#   SHARED_DIR   - shared directory between steps (params.env, gh-token, kubeconfig)
#   ARTIFACT_DIR - artifact output directory
#
# Required credentials:
#   OPENAI_API_KEY or OPENAI_API_KEY_PATH (mounted from the oap-lts-codex-sa secret)
#   ${SHARED_DIR}/gh-token (minted by openspec-mint-gh-token from the
#   openshift-app-platform-shift-github-bot GitHub App)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENSPEC_SRC="${OPENSPEC_SRC:-/opt/openspec-src}"
WORKSPACE="${WORKSPACE:-/workspace}"
WORKFLOW="${WORKFLOW:-${1:-}}"

CODEX_MODEL="${CODEX_MODEL:-gpt-5.6-sol}"
AGENT_EFFORT="${AGENT_EFFORT:-}"
OPENAI_API_KEY_PATH="${OPENAI_API_KEY_PATH:-/var/run/codex-openai-api-key/openai_api_key}"

# Per-round Codex budgets (seconds). The pod-level step timeout (4h agile /
# 3h qe) must stay above initial + rounds * resume.
CODEX_TIMEOUT_INITIAL="${CODEX_TIMEOUT_INITIAL:-3600}"
CODEX_TIMEOUT_RESUME="${CODEX_TIMEOUT_RESUME:-1200}"
if [[ -z "${MAX_RESUME_ROUNDS:-}" ]]; then
  case "${WORKFLOW}" in
    agile) MAX_RESUME_ROUNDS=8 ;;
    qe)    MAX_RESUME_ROUNDS=6 ;;
    *)     MAX_RESUME_ROUNDS=6 ;;
  esac
fi

log() { echo "[openspec-${WORKFLOW:-?}] $*"; }

fail() {
  log "ERROR: $*"
  exit 1
}

# ---------------------------------------------------------------------------
# Environment and secrets
# ---------------------------------------------------------------------------

[[ -n "${SHARED_DIR:-}" && -n "${ARTIFACT_DIR:-}" ]] || fail "SHARED_DIR and ARTIFACT_DIR must be set by ci-operator"
[[ -f "${SHARED_DIR}/params.env" ]] || fail "${SHARED_DIR}/params.env not found — was the extract-params pre-step run?"
# shellcheck disable=SC1091
source "${SHARED_DIR}/params.env"

case "${WORKFLOW}" in
  agile|qe) ;;
  *) fail "WORKFLOW must be 'agile' or 'qe' (got '${WORKFLOW}')" ;;
esac

# OpenAI API key — never echo the value.
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  [[ -r "${OPENAI_API_KEY_PATH}" ]] || fail "OpenAI API key not found at ${OPENAI_API_KEY_PATH} (oap-lts-codex-sa secret)"
  OPENAI_API_KEY="$(<"${OPENAI_API_KEY_PATH}")"
  export OPENAI_API_KEY
fi
export CODEX_API_KEY="${CODEX_API_KEY:-${OPENAI_API_KEY}}"
log "OpenAI API key loaded."

# GitHub App token minted by the openspec-mint-gh-token pre-step.
[[ -f "${SHARED_DIR}/gh-token" ]] || fail "${SHARED_DIR}/gh-token not found — was openspec-mint-gh-token run?"
GH_TOKEN="$(<"${SHARED_DIR}/gh-token")"
export GH_TOKEN
log "GitHub App token loaded."

# Optional per-run model/effort overrides from the input Dockerfile.
[[ -n "${MODEL:-}" ]] && CODEX_MODEL="${MODEL}"
[[ -n "${EFFORT:-}" ]] && AGENT_EFFORT="${EFFORT}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# owner/repo from any GitHub URL form
slug_from_url() {
  local url="$1"
  url="${url#https://}"
  url="${url#http://}"
  url="${url#git@github.com:}"
  url="${url#github.com/}"
  url="${url%/}"
  url="${url%.git}"
  echo "${url#github.com/}"
}

# Strip YAML frontmatter (leading --- ... --- block) from a command markdown.
strip_frontmatter() {
  awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next} fm==1 && /^---[[:space:]]*$/ {fm=2; next} fm!=1 {print}' "$1"
}

codex_exec() { # $1=prompt $2=timeout-seconds
  local prompt="$1" tmo="$2" rc=0
  local -a args=(exec --cd "${CLONE_PATH}" --sandbox danger-full-access --color never -m "${CODEX_MODEL}")
  [[ -n "${AGENT_EFFORT}" ]] && args+=(-c "model_reasoning_effort=${AGENT_EFFORT}")
  args+=(-o "${ARTIFACT_DIR}/codex-last-message.txt")
  timeout --signal=INT --kill-after=60 "${tmo}" codex "${args[@]}" "${prompt}" \
    >>"${ARTIFACT_DIR}/codex-session.log" 2>&1 || rc=$?
  if [[ -s "${ARTIFACT_DIR}/codex-last-message.txt" ]]; then
    echo "--- last agent message ---" >>"${ARTIFACT_DIR}/codex-session.log"
    cat "${ARTIFACT_DIR}/codex-last-message.txt" >>"${ARTIFACT_DIR}/codex-session.log"
  fi
  return "${rc}"
}

codex_resume() { # $1=follow-up prompt $2=timeout-seconds
  local prompt="$1" tmo="$2" rc=0
  local -a args=(exec --cd "${CLONE_PATH}" --sandbox danger-full-access --color never -m "${CODEX_MODEL}")
  [[ -n "${AGENT_EFFORT}" ]] && args+=(-c "model_reasoning_effort=${AGENT_EFFORT}")
  args+=(resume --last -o "${ARTIFACT_DIR}/codex-last-message.txt")
  timeout --signal=INT --kill-after=60 "${tmo}" codex "${args[@]}" "${prompt}" \
    >>"${ARTIFACT_DIR}/codex-session.log" 2>&1 || rc=$?
  if [[ -s "${ARTIFACT_DIR}/codex-last-message.txt" ]]; then
    echo "--- last agent message ---" >>"${ARTIFACT_DIR}/codex-session.log"
    cat "${ARTIFACT_DIR}/codex-last-message.txt" >>"${ARTIFACT_DIR}/codex-session.log"
  fi
  return "${rc}"
}

collect_pr_urls() {
  cat "${ARTIFACT_DIR}/codex-last-message.txt" 2>/dev/null || true
  grep -hEo 'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+' \
    "${ARTIFACT_DIR}/codex-session.log" 2>/dev/null || true
}

workflow_complete() {
  local urls url
  urls="$(collect_pr_urls | grep -Eo 'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+' | sort -u || true)"
  if [[ -n "${urls}" ]]; then
    while read -r url; do
      if gh pr view "${url}" --json state,url >/dev/null 2>&1; then
        log "Verified PR: ${url}"
        return 0
      fi
    done <<<"${urls}"
  fi
  # QE Design Mode (ADR/EP only): completion is generated test code, no PR.
  if [[ "${WORKFLOW}" == "qe" && -z "${PR_URL:-}" ]]; then
    if ls "${CLONE_PATH}/openspec/changes/${CHANGE_NAME}/e2e/generated/"*_test.go >/dev/null 2>&1; then
      log "Design Mode artifacts generated."
      return 0
    fi
  fi
  return 1
}

state_summary() {
  local dir="${CLONE_PATH}/openspec/changes/${CHANGE_NAME}"
  if [[ -d "${dir}" ]]; then
    echo "Artifacts under openspec/changes/${CHANGE_NAME}:"
    find "${dir}" -maxdepth 2 -type f | sed "s|${CLONE_PATH}/||" | head -40
  else
    echo "No change directory yet at openspec/changes/${CHANGE_NAME}."
  fi
  if [[ -f "${dir}/implementation/state.yaml" ]]; then
    echo "implementation/state.yaml:"
    cat "${dir}/implementation/state.yaml"
  fi
}

collect_artifacts() {
  log "Collecting artifacts..."
  local dir="${CLONE_PATH}/openspec/changes/${CHANGE_NAME:-}"
  if [[ -n "${CHANGE_NAME:-}" && -d "${dir}" ]]; then
    tar -czf "${ARTIFACT_DIR}/openspec-changes-${CHANGE_NAME}.tar.gz" -C "${CLONE_PATH}" "openspec/changes/${CHANGE_NAME}" || true
    cp "${dir}/telemetry/metrics-report.json" "${ARTIFACT_DIR}/" 2>/dev/null || true
    cp "${dir}/telemetry/qe-metrics.json" "${ARTIFACT_DIR}/" 2>/dev/null || true
  fi
  if [[ -d "${HOME}/.codex/sessions" ]]; then
    tar -czf "${ARTIFACT_DIR}/codex-sessions.tar.gz" -C "${HOME}/.codex" sessions/ || true
  fi
}

write_junit() { # $1=passed(0/1) $2=message
  local passed="$1" message="$2"
  local failure=""
  if [[ "${passed}" != "0" ]]; then
    failure="<failure message=\"workflow did not complete\">${message}</failure>"
  fi
  cat >"${ARTIFACT_DIR}/junit_openspec.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="openspec-${WORKFLOW}" tests="1" failures="${passed}" time="0">
  <testcase name="openspec ${WORKFLOW} workflow end-to-end">${failure}</testcase>
</testsuite>
EOF
}

trap collect_artifacts EXIT

gh auth setup-git || fail "gh auth setup-git failed"

# ---------------------------------------------------------------------------
# Workflow inputs and workspace setup
# ---------------------------------------------------------------------------

mkdir -p "${WORKSPACE}"

if [[ "${WORKFLOW}" == "agile" ]]; then
  # --- validate inputs ---
  [[ -n "${JIRA_KEY:-}" ]] || fail "JIRA_KEY is required (agile-workflow.Dockerfile)"
  [[ -n "${TARGET_REPO:-}" ]] || fail "TARGET_REPO is required (agile-workflow.Dockerfile)"
  TARGET_SLUG="$(slug_from_url "${TARGET_REPO}")"
  [[ "${TARGET_SLUG}" == */* ]] || fail "Cannot parse owner/repo from TARGET_REPO=${TARGET_REPO}"
  REPO_NAME="${TARGET_SLUG##*/}"
  CLONE_PATH="${WORKSPACE}/${REPO_NAME}"
  CHANGE_NAME="${CHANGE_NAME:-}"
  if [[ -z "${CHANGE_NAME}" ]]; then
    CHANGE_NAME="$(echo "${JIRA_KEY##*/}" | tr '[:upper:]' '[:lower:]')"
  fi
  FAST_TRACK="${FAST_TRACK:-false}"

  [[ -f "${SHARED_DIR}/jira-spec.md" ]] || fail "${SHARED_DIR}/jira-spec.md not found — commit the Jira ticket content as prow-workflow/jira-spec.md in your PR"
  if grep -q "OPENSPEC-JIRA-SPEC-PLACEHOLDER" "${SHARED_DIR}/jira-spec.md"; then
    fail "prow-workflow/jira-spec.md still contains the placeholder — replace it with the Jira ticket content (${JIRA_KEY}) before running the workflow"
  fi
  cp "${SHARED_DIR}/jira-spec.md" /tmp/jira-spec.md

  # --- fork + clone (best effort; the agent completes setup if this fails) ---
  if [[ ! -d "${CLONE_PATH}/.git" ]]; then
    log "Forking ${TARGET_SLUG} (if needed) and cloning..."
    if gh repo fork "${TARGET_SLUG}" --clone=false >"${WORKSPACE}/fork.log" 2>&1 || true; then
      FORK_SLUG="$(grep -oE '[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' "${WORKSPACE}/fork.log" | head -1 || true)"
    fi
    if [[ -n "${FORK_SLUG:-}" && "${FORK_SLUG}" != "${TARGET_SLUG}" ]]; then
      gh repo clone "${FORK_SLUG}" "${CLONE_PATH}" || log "WARN: clone of ${FORK_SLUG} failed — the agent will fork/clone itself"
    else
      log "WARN: could not determine fork slug — the agent will fork/clone itself"
    fi
  fi

elif [[ "${WORKFLOW}" == "qe" ]]; then
  # --- validate inputs ---
  PR_URL="${PR_URL:-}"
  ADR_URL="${ADR_URL:-}"
  EP_URL="${EP_URL:-}"
  if [[ -z "${PR_URL}" && -z "${ADR_URL}" && -z "${EP_URL}" ]]; then
    fail "At least one of PR_URL, ADR_URL or EP_URL is required (qe-workflow.Dockerfile)"
  fi

  if [[ -n "${PR_URL}" ]]; then
    PR_PATH="${PR_URL#https://github.com/}"
    PR_PATH="${PR_PATH#github.com/}"
    PR_PATH="${PR_PATH%/}"
    PR_SLUG="${PR_PATH%/pull/*}"
    PR_NUM="${PR_PATH##*/}"
    [[ "${PR_SLUG}" == */* && "${PR_NUM}" =~ ^[0-9]+$ ]] || fail "Cannot parse owner/repo and PR number from PR_URL=${PR_URL}"
    TARGET_SLUG="${PR_SLUG}"
    REPO_NAME="${PR_SLUG##*/}"
    CLONE_PATH="${WORKSPACE}/${REPO_NAME}"
    CHANGE_NAME="${CHANGE_NAME:-pr-${PR_NUM}-e2e}"

    log "Cloning ${PR_SLUG} and checking out PR #${PR_NUM}..."
    gh repo clone "${PR_SLUG}" "${CLONE_PATH}"
    ( cd "${CLONE_PATH}" && gh pr checkout "${PR_NUM}" )
  else
    # Design Mode — clone target repo if resolvable, else let the agent set up.
    CHANGE_NAME="${CHANGE_NAME:-e2e-design}"
    if [[ -n "${TARGET_REPO:-}" ]]; then
      TARGET_SLUG="$(slug_from_url "${TARGET_REPO}")"
      REPO_NAME="${TARGET_SLUG##*/}"
      CLONE_PATH="${WORKSPACE}/${REPO_NAME}"
      gh repo clone "${TARGET_SLUG}" "${CLONE_PATH}" || true
    else
      CLONE_PATH="${WORKSPACE}/design"
      mkdir -p "${CLONE_PATH}"
    fi
  fi

  # --- cluster (provisioned by the ipi-aws-pre chain) ---
  if [[ -f "${SHARED_DIR}/kubeconfig" ]]; then
    export KUBECONFIG="${SHARED_DIR}/kubeconfig"
    log "KUBECONFIG set from ${SHARED_DIR}/kubeconfig."
    oc whoami >/dev/null 2>&1 && log "Cluster reachable: $(oc whoami --show-server 2>/dev/null || echo '(server unknown)')" || log "WARN: cluster not reachable yet via oc."
  else
    log "WARN: no kubeconfig in ${SHARED_DIR} — E2E execution will be skipped by the workflow."
  fi
fi

# The agent needs a git repo to work in; make sure CLONE_PATH exists even if
# the best-effort clone above failed (the agent will fork/clone per the prompt).
mkdir -p "${CLONE_PATH}"
cd "${CLONE_PATH}"

# ---------------------------------------------------------------------------
# Install openspec scaffolding into the workspace repo
# ---------------------------------------------------------------------------

log "Installing openspec scaffolding into ${CLONE_PATH}..."
openspec init --tools cursor >/dev/null 2>&1 || true
rm -rf openspec .cursor
cp -r "${OPENSPEC_SRC}/openspec" ./openspec
mkdir -p .cursor
cp -r "${OPENSPEC_SRC}/commands" .cursor/commands
mkdir -p openspec/changes

# Keep the scaffolding and workflow artifacts out of any raised PR.
{
  echo ""
  echo "# --- openspec CI scaffolding (never commit) ---"
  echo "openspec/"
  echo ".cursor/"
} >>.gitignore 2>/dev/null || true

# Seed runtime configuration (cluster kubeconfig for QE; github stays in env).
if [[ "${WORKFLOW}" == "qe" && -n "${KUBECONFIG:-}" ]]; then
  python3.11 - "$KUBECONFIG" <<'PYEOF'
import sys, yaml
path = "openspec/config.yaml"
with open(path) as f:
    cfg = yaml.safe_load(f) or {}
cfg.setdefault("credentials", {}).setdefault("cluster", {})["kubeconfig_path"] = sys.argv[1]
with open(path, "w") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
PYEOF
fi

log "Workspace ready: ${CLONE_PATH} (change: ${CHANGE_NAME})"

# ---------------------------------------------------------------------------
# Build the initial prompt
# ---------------------------------------------------------------------------

if [[ "${WORKFLOW}" == "agile" ]]; then
  CMD_ARGS="${JIRA_KEY}"
  [[ -n "${CHANGE_NAME}" ]] && CMD_ARGS="${CMD_ARGS} ${CHANGE_NAME}"
  [[ "${FAST_TRACK}" == "true" ]] && CMD_ARGS="${CMD_ARGS} --fast-track"
  CMD_ARGS="${CMD_ARGS} ${TARGET_REPO} ${CLONE_PATH}"
  COMMAND_MD="${OPENSPEC_SRC}/commands/opsx-new.md"

  CI_CONTEXT=$(cat <<EOF

## Non-interactive CI execution context — overrides for this run

You are executing this command as a NON-INTERACTIVE Codex CLI run on OpenShift CI. Apply the following to everything in the command instructions above:

1. **Inputs (already provided — never ask for them):**
   - Jira ticket: ${JIRA_KEY}
   - Target repo (upstream): ${TARGET_REPO}
   - Local clone path: ${CLONE_PATH}
   - Change name: ${CHANGE_NAME}
   - Workflow mode: $([[ "${FAST_TRACK}" == "true" ]] && echo fast-track || echo full)

2. **No MCP servers.** Jira MCP and GitHub MCP are unavailable. Use the \`gh\` CLI (GH_TOKEN is already exported and authenticated) for all GitHub operations (fork, clone, PR create) and \`git\` for branching/commits. The Jira ticket content is pre-provided at /tmp/jira-spec.md — at the "Fetch ticket + epic metadata" step, copy it to openspec/changes/${CHANGE_NAME}/inputs/jira-spec.md, derive the metadata you can from it, set jira_fetched_at, and do NOT ask the user to paste anything. Leave epic fields empty when unknown.

3. **Slash commands are files.** The openspec commands are markdown files in \`.cursor/commands/\`. When any step instructs you to run another /opsx-<name> [args] command (including the auto-chained /opsx-continue and /opsx-apply), read \`.cursor/commands/opsx-<name>.md\` and execute its instructions with those arguments in this same session.

4. **Pre-answered gates** (auto_approve: true is set in openspec/config.yaml):
   - Artifact, task and phase approvals: auto-approved — never stop or ask.
   - **PR creation gate: PRE-APPROVED.** When implementation completes, immediately raise the PR from the fork to upstream with \`gh pr create\` without asking anyone.
   - **Jira Story creation: SKIP entirely** — there are no Jira credentials on CI.
   - If agents.md or harness-evals/constitution.md is missing from the repo, STOP and report exactly which file is missing — never generate them yourself.

5. **Workspace:** the fork clone should be at ${CLONE_PATH}. If it is missing or its origin is not a valid fork of ${TARGET_REPO}, fork with \`gh repo fork ${TARGET_SLUG} --clone=false\`, clone your fork to ${CLONE_PATH}, and continue as instructed.

6. **Completion:** when the workflow is done, print a final summary and list every PR you created on its own line in the form \`PR_CREATED: <PR-URL>\`.
EOF
  )
else
  CMD_ARGS="${CHANGE_NAME}"
  [[ -n "${PR_URL:-}" ]] && CMD_ARGS="${CMD_ARGS} --pr ${PR_URL}"
  [[ -n "${ADR_URL:-}" ]] && CMD_ARGS="${CMD_ARGS} --adr ${ADR_URL}"
  [[ -n "${EP_URL:-}" ]] && CMD_ARGS="${CMD_ARGS} --ep ${EP_URL}"
  [[ -n "${PHASE:-}" ]] && CMD_ARGS="${CMD_ARGS} --phase ${PHASE}"
  COMMAND_MD="${OPENSPEC_SRC}/commands/opsx-e2e.md"

  CI_CONTEXT=$(cat <<EOF

## Non-interactive CI execution context — overrides for this run

You are executing this command as a NON-INTERACTIVE Codex CLI run on OpenShift CI. Apply the following to everything in the command instructions above:

1. **Inputs (already provided — never ask for them):**
   - Change name: ${CHANGE_NAME}
   $([[ -n "${PR_URL:-}" ]] && echo "- PR URL: ${PR_URL}" || true)
   $([[ -n "${ADR_URL:-}" ]] && echo "- ADR: ${ADR_URL}" || true)
   $([[ -n "${EP_URL:-}" ]] && echo "- EP: ${EP_URL}" || true)
   $([[ -n "${PHASE:-}" ]] && echo "- Phase: ${PHASE}" || true)
   $([[ -n "${TARGET_SLUG:-}" ]] && echo "- Target repo: https://github.com/${TARGET_SLUG}" || true)

2. **No MCP servers.** Use the \`gh\` CLI (GH_TOKEN is already exported and authenticated) for all GitHub operations, and \`git\` for branching/commits. Fetch the PR diff/metadata with \`gh pr view\`/\`gh pr diff\`; fetch ADR/EP content with \`curl\`.

3. **Slash commands are files.** The openspec commands are markdown files in \`.cursor/commands/\`. When a step references another /opsx-<name> command, read \`.cursor/commands/opsx-<name>.md\` and execute it in this same session.

4. **Pre-answered gates:**
   - Every stage approval gate: approved — never stop or ask.
   - **"Run E2E tests locally?" → YES.** A freshly provisioned OpenShift cluster is available: KUBECONFIG is exported (\`${KUBECONFIG:-not set}\`) and \`oc\` is installed. At the cluster readiness gate, if the operator is not yet deployed, deploy it first following qe-e2e/qe-behaviour.md Section 3a (build from the PR branch when needed) before running the tests.
   - **Push gate: PRE-APPROVED.** Push the generated E2E tests. If the PR head branch is not writable with this token (usual case), fork the target repo with \`gh repo fork\`, push a branch with the test commits to the fork, and open a PR against the base branch of the target repo with \`gh pr create\`. If the head branch IS writable, push to the existing PR branch instead.
   - If agents.md or harness-evals/constitution.md is missing from the repo, STOP and report exactly which file is missing — never generate them yourself.

5. **Completion:** when the workflow is done, print a final summary and list every PR you created on its own line in the form \`PR_CREATED: <PR-URL>\`. In Design Mode (no PR input), summarize the generated artifacts under openspec/changes/${CHANGE_NAME}/e2e/ instead.
EOF
  )
fi

[[ -f "${COMMAND_MD}" ]] || fail "Command prompt not found: ${COMMAND_MD}"
PROMPT="$(strip_frontmatter "${COMMAND_MD}")

## Invocation

/$( [[ "${WORKFLOW}" == "agile" ]] && echo opsx-new || echo opsx-e2e ) ${CMD_ARGS}
${CI_CONTEXT}"

log "Starting Codex (${CODEX_MODEL}, effort: ${AGENT_EFFORT:-default}) for the ${WORKFLOW} workflow..."
codex_exec "${PROMPT}" "${CODEX_TIMEOUT_INITIAL}" || log "WARN: initial Codex run exited non-zero (see codex-session.log)"

# ---------------------------------------------------------------------------
# Gate loop — resume until the workflow completes or rounds are exhausted
# ---------------------------------------------------------------------------

RESUME_DIRECTIVE="Continue the openspec ${WORKFLOW} workflow for change \"${CHANGE_NAME}\" in this same workspace until it is fully complete. This is a NON-INTERACTIVE CI run: never ask questions, auto-approve every gate, and when a step references a /opsx-* command, read .cursor/commands/<name>.md and follow it. If you are waiting on any approval, the answer is: proceed. $( [[ "${WORKFLOW}" == "agile" ]] && echo 'If implementation is complete, raise the PR now (gh pr create) and report its URL.' || echo 'Generate remaining E2E stages, deploy and run the tests on the provided cluster if not done, then push the tests and raise the PR (gh pr create).' ) When fully done, print a final summary including PR_CREATED: <url> lines.

Current workspace state:
$(state_summary)"

ROUND=0
while ! workflow_complete; do
  ROUND=$((ROUND + 1))
  if [[ "${ROUND}" -gt "${MAX_RESUME_ROUNDS}" ]]; then
    log "Workflow did not complete after ${MAX_RESUME_ROUNDS} resume rounds."
    write_junit 1 "openspec ${WORKFLOW} workflow did not complete within ${MAX_RESUME_ROUNDS} resume rounds"
    collect_pr_urls | grep -Eo 'https://github\.com/[^ ]+/pull/[0-9]+' | sort -u || true
    exit 1
  fi
  log "Workflow not complete — resuming Codex (round ${ROUND}/${MAX_RESUME_ROUNDS})..."
  if ! codex_resume "${RESUME_DIRECTIVE}" "${CODEX_TIMEOUT_RESUME}"; then
    log "WARN: resume round ${ROUND} exited non-zero — continuing to check completion."
  fi
done

# ---------------------------------------------------------------------------
# Success — report results
# ---------------------------------------------------------------------------

log "Workflow complete."
write_junit 0 ""

echo "=== openspec ${WORKFLOW} workflow completed ==="
echo "Change artifacts: openspec/changes/${CHANGE_NAME}/ (archived to ${ARTIFACT_DIR}/openspec-changes-${CHANGE_NAME}.tar.gz)"
PR_URLS="$(collect_pr_urls | grep -Eo 'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[0-9]+' | sort -u || true)"
if [[ -n "${PR_URLS}" ]]; then
  while read -r url; do
    echo "PR_CREATED: ${url}"
  done <<<"${PR_URLS}"
elif [[ "${WORKFLOW}" == "qe" && -z "${PR_URL:-}" ]]; then
  echo "DESIGN_MODE_COMPLETE: artifacts under openspec/changes/${CHANGE_NAME}/e2e/"
else
  log "WARN: no PR URLs reported by the agent — check codex-session.log."
fi
