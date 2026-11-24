---
name: /opsx-publish-metrics
id: opsx-publish-metrics
category: Workflow
description: Publish metrics-report.json and qe-metrics.json to open-spec-mado on main (direct push, no MR)
argument-hint: "[change-name]"
---

Publish a change's telemetry (`metrics-report.json` and, if present, `qe-metrics.json`) to
[anankuma/open-spec-mado](https://gitlab.cee.redhat.com/anankuma/open-spec-mado) on **`main`**
via a direct commit and push to upstream `main` (MR fallback if push denied): copy files under
`data/open-spec-matrics/operators/<operator>/`, commit, and `git push origin main`.

Run only after **`/opsx-archive`** has captured productivity feedback — pre-push guards
hard-block incomplete reports.

This is a **standalone command**, run manually whenever you want to publish — it is
NOT triggered automatically by `/opsx-archive`.

**Input**: Optionally specify a change name. If omitted, check conversation context;
if still ambiguous, list both active changes (`openspec list --json`) and archived
changes (`ls openspec/changes/archive/`) and let the user pick via **AskQuestion**.

## Steps

### 0. GitLab authentication (MANDATORY — do not skip)

**This step runs FIRST, before resolving telemetry or touching the dashboard repo.
Do NOT proceed to step 1 until authentication is verified.**

1. Verify `glab` is installed:
   ```bash
   command -v glab
   ```
   If missing → STOP: "Install glab first (`dnf install glab` or https://gitlab.com/gitlab-org/cli)."

2. If `glab api user` fails with keyring but works in the user's GUI terminal, set
   `export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"` and `unset GITLAB_TOKEN`
   so glab uses the OS keyring (never echo tokens).

3. Check existing auth:
   ```bash
   glab auth status --hostname gitlab.cee.redhat.com 2>&1
   ```
   Or verify API: `glab api user` returns your username.

4. **If already authenticated** for `gitlab.cee.redhat.com` → skip to step 8 (git protocol).

5. **If NOT authenticated**, STOP and prompt the user:

   ```
   Before publishing metrics, export your GitLab token in the terminal.
   Do NOT paste the token in chat.

   export GITLAB_TOKEN='your-legacy-api-access-token'

   Create a Personal Access Token (legacy API access, api scope) at:
   https://gitlab.cee.redhat.com/-/user_settings/personal_access_tokens

   Reply 'done' when exported.
   ```

6. **Do NOT proceed** until the user replies `done` or `yes`.

7. Verify the token is set (never echo or log the value):
   ```bash
   [ -n "$GITLAB_TOKEN" ] && echo "GITLAB_TOKEN is set" || echo "GITLAB_TOKEN is NOT set"
   ```
   If NOT set → STOP: "GITLAB_TOKEN is not set in this shell. Export it in the
   Cursor integrated terminal and reply 'done' again."

8. **Ask git protocol** (use **AskQuestion**):
   - **HTTPS (Recommended)** — default for token auth; clone/push via `https://gitlab.cee.redhat.com/...`
   - **SSH** — clone/push via `git@gitlab.cee.redhat.com:...` (requires SSH key configured)

   Default to **SSH** when `glab auth status` shows SSH configured and the user skips.

9. Log in non-interactively using the exported token (skip if step 4 already authenticated):
   ```bash
   glab auth login \
     --hostname gitlab.cee.redhat.com \
     --token "$GITLAB_TOKEN" \
     --git-protocol <https|ssh>
   ```

10. Verify login succeeded:
    ```bash
    glab auth status --hostname gitlab.cee.redhat.com
    glab api user
    ```
    If verification fails → STOP with the error output. Do not continue.

11. Persist the chosen protocol for this run as `GIT_PROTOCOL` (`https` or `ssh`).

**Security guardrails for this step:**
- NEVER ask the user to paste the token in chat
- NEVER run `echo $GITLAB_TOKEN` or log the token in command output
- NEVER commit or write the token to any file

### 1. Resolve the change and locate its telemetry files

The change may already be archived (moved to `openspec/changes/archive/YYYY-MM-DD-<name>/`)
or still live (`openspec/changes/<name>/`). Check both locations, preferring the
archived one if both somehow exist. Also accept change dirs at the repo root when used
outside `openspec/changes/` (same `telemetry/` layout).

```bash
ls openspec/changes/archive/*-<name>/telemetry/ 2>/dev/null
ls openspec/changes/<name>/telemetry/ 2>/dev/null
ls <name>/telemetry/ 2>/dev/null
```

Read whichever of these exist from the resolved directory:
- `telemetry/metrics-report.json` (development metrics — required for publish)
- `telemetry/qe-metrics.json` (QE/E2E metrics — only if `/opsx-e2e` ran for this change)

**If `metrics-report.json` does not exist:** STOP — "No development telemetry found for
`<name>`. Run `/opsx-apply` (and `/opsx-archive`) first." Do not proceed.

### 2. Pre-push publish guard (HARD BLOCK — before touching GitLab)

Run guards on staging copies in a temp directory. **Do not clone the dashboard repo**
until all guards pass.

#### 2a. Prepare staging JSON (allowed normalization only)

For each file to publish, copy the source to `$STAGED_DIR/<basename>` then apply **only**
this metadata fix:

- If `jira_epic_name` is empty/null/whitespace **and** `jira_task_name` is non-empty after
  trim → set `jira_epic_name` to `jira_task_name` in the staging copy.

Use a short Python script (preferred) or `jq` — never hand-edit token counts, phases,
tasks, or productivity numbers.

```bash
STAGED_DIR="$(mktemp -d)"
SRC_METRICS="<path-to-change>/telemetry/metrics-report.json"
SRC_QE="<path-to-change>/telemetry/qe-metrics.json"   # omit if missing

cp "$SRC_METRICS" "$STAGED_DIR/metrics-report.json"
test -f "$SRC_QE" && cp "$SRC_QE" "$STAGED_DIR/qe-metrics.json"

python3 <<'PY'
import json, sys
from pathlib import Path

STAGED = Path(sys.argv[1])

def nonempty(s):
    return bool(s and str(s).strip())

def guard_metrics(path: Path) -> None:
    data = json.loads(path.read_text())
    task = data.get("jira_task_name") or ""
    link = data.get("jira_task_link") or ""
    if not nonempty(task):
        sys.exit(f"STOP: {path.name}: jira_task_name is empty. Fix inputs/jira.yaml (jira_summary) and regenerate the report.")
    if not nonempty(link):
        sys.exit(f"STOP: {path.name}: jira_task_link is empty. Ensure jira_key is set and regenerate the report.")
    if not nonempty(data.get("jira_epic_name") or ""):
        data["jira_epic_name"] = task.strip()
    if not nonempty(data.get("jira_epic_name")):
        sys.exit(f"STOP: {path.name}: jira_epic_name and jira_task_name are both empty.")
    pm = data.get("productivity_metrics")
    if pm is None:
        sys.exit(f"STOP: {path.name}: productivity_metrics not captured. Run /opsx-archive first.")
    rs = data.get("report_status") or {}
    if rs.get("complete") is not True:
        missing = rs.get("missing_fields") or []
        sys.exit(f"STOP: {path.name}: report incomplete (missing: {missing}). Run /opsx-archive first.")
    if pm.get("story_points_delivered") is None:
        sys.exit(f"STOP: {path.name}: productivity_metrics.story_points_delivered is missing.")
    path.write_text(json.dumps(data, indent=2) + "\n")

def guard_qe(path: Path) -> None:
    data = json.loads(path.read_text())
    task = data.get("jira_task_name") or ""
    link = data.get("jira_task_link") or ""
    if not nonempty(task):
        sys.exit(f"STOP: {path.name}: jira_task_name is empty.")
    if not nonempty(link):
        sys.exit(f"STOP: {path.name}: jira_task_link is empty.")
    if not nonempty(data.get("jira_epic_name") or "") and nonempty(task):
        data["jira_epic_name"] = task.strip()
    qpm = data.get("qe_productivity_metrics") or data.get("productivity_metrics")
    qrs = data.get("qe_report_status") or data.get("report_status") or {}
    if qpm is None:
        sys.exit(f"STOP: {path.name}: QE productivity not captured. Complete QE archive prompts.")
    if qrs.get("complete") is not True:
        missing = qrs.get("missing_fields") or []
        sys.exit(f"STOP: {path.name}: QE report incomplete (missing: {missing}).")
    path.write_text(json.dumps(data, indent=2) + "\n")

guard_metrics(STAGED / "metrics-report.json")
qe = STAGED / "qe-metrics.json"
if qe.is_file():
    guard_qe(qe)
PY "$STAGED_DIR"
```

On any STOP message → exit the command and show the user how to fix (`/opsx-archive`,
`inputs/jira.yaml`, regenerate telemetry). **Do not offer "publish anyway".**

#### 2b. Operator folder (optional override)

Read `operator_name` from staged `metrics-report.json`. If empty or clearly wrong for the
operator repo (e.g. `openspec` when the user says `cert-manager`), use **AskQuestion** once:
**"Dashboard operator folder? (default: `<normalized operator_name>`)"** — normalize:
lowercase, hyphens → underscores (`cert-manager` → `cert_manager`).

If only `qe-metrics.json` is published (should not happen — dev metrics required), derive
from `git remote get-url origin` the same way as `telemetry/report.py`.

### 3. Determine filenames

Read `jira_key` from `metrics-report.json → run.jira_key` or `jira_task_link` (trailing
segment) or from `inputs/jira.yaml → jira_key`.

Read `codegen_mode` from `openspec/config.yaml → flags.codegen_mode` (default: `direct`).

ASK the user: **"What model was primarily used for this run? (e.g. `composer-2.5`,
`sonnet-5`, `opus`) — press Enter to skip."**
- If provided: `model_slug` = the answer, lowercased, spaces → hyphens.
- If skipped: omit the model segment entirely from the filename.

Build target filenames:

| File | Target path |
|------|-------------|
| Staged dev metrics | `data/open-spec-matrics/operators/<operator>/<JIRA_KEY>-<codegen_mode>[-<model_slug>]-metrics-report.json` |
| Staged qe metrics (if any) | `data/open-spec-matrics/operators/<operator>/QE/<JIRA_KEY>-qe-metrics.json` |

### 4. Clone dashboard repo on `main`

```bash
GITLAB_REPO="anankuma/open-spec-mado"
WORK_DIR="$(mktemp -d)"
```

| `GIT_PROTOCOL` | Clone URL |
|----------------|-----------|
| `https` | `https://gitlab.cee.redhat.com/anankuma/open-spec-mado.git` |
| `ssh` | `git@gitlab.cee.redhat.com:anankuma/open-spec-mado.git` |

```bash
git clone --branch main "$CLONE_URL" "$WORK_DIR/open-spec-mado"
cd "$WORK_DIR/open-spec-mado"
git pull --ff-only origin main
```

If clone/pull fails → STOP with error.

### 5. Copy staged files, commit

```bash
OPERATOR_DIR="data/open-spec-matrics/operators/<operator>"
mkdir -p "$OPERATOR_DIR"
cp "$STAGED_DIR/metrics-report.json" "$OPERATOR_DIR/<dev-filename>"

# Only if qe-metrics was staged in step 2:
mkdir -p "$OPERATOR_DIR/QE"
cp "$STAGED_DIR/qe-metrics.json" "$OPERATOR_DIR/QE/<qe-filename>"

git add "$OPERATOR_DIR/"
git commit -m "Add <JIRA_KEY> metrics for <operator>"
```

Single atomic commit for both files when QE is included.

### 6. Push to upstream `main` (preferred)

```bash
git push origin main
```

- **On success** → continue to step 8 (report **direct** success).
- **On permission denied** (`not allowed to push`, `403`, `deny updating a protected ref`) →
  **do not stop** — run **step 6b (MR fallback)** using the **same commit** already created
  in step 5 (do not re-run guards or change staged file content).

### 6b. MR fallback (no write access to upstream `main`)

Use when step 6 fails. Goal: push the metrics commit to **your fork** on a short-lived branch
and open an MR into `anankuma/open-spec-mado` `main`.

1. **Resolve GitLab username** (required for `--head`):
   ```bash
   export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
   GL_USER=$(glab api user 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['username'])")
   test -n "$GL_USER" || GL_USER=$(glab auth status --hostname gitlab.cee.redhat.com 2>&1 | grep -oP 'Logged in to .* as \K\S+' | head -1)
   ```
   If empty → STOP (auth broken).

2. **Ensure fork exists:**
   ```bash
   glab repo fork anankuma/open-spec-mado --clone=false 2>/dev/null || true
   ```

3. **Branch name** (from repo cwd after step 5):
   ```bash
   BRANCH="metrics/<jira-key-lowercase>-$(date +%Y%m%d-%H%M)"
   ```

4. **Push commit to fork** (still in `$WORK_DIR/open-spec-mado`; `origin` is upstream):
   ```bash
   # GIT_PROTOCOL ssh (default):
   FORK_PUSH="git@gitlab.cee.redhat.com:${GL_USER}/open-spec-mado.git"
   # or https:
   # FORK_PUSH="https://gitlab.cee.redhat.com/${GL_USER}/open-spec-mado.git"

   git branch "$BRANCH"
   git push "$FORK_PUSH" "$BRANCH:$BRANCH"
   ```
   If push fails → STOP with fork push error.

5. **Open MR** (attempt; degrade gracefully):
   ```bash
   glab mr create \
     --repo anankuma/open-spec-mado \
     --head "${GL_USER}/open-spec-mado" \
     --source-branch "$BRANCH" \
     --target-branch main \
     --title "Add <JIRA_KEY> metrics — <operator>" \
     --description "$(cat <<'EOF'
   ## Metrics for <JIRA_KEY> (<operator>)

   Publish staged telemetry to `data/open-spec-matrics/operators/<operator>/`.
   Generated by `/opsx-publish-metrics` (MR fallback — no upstream main write access).
   EOF
   )" \
     --yes
   ```

   **If `glab mr create` fails:** report **partial success** — fork branch URL + manual MR link:
   `https://gitlab.cee.redhat.com/anankuma/open-spec-mado/-/merge_requests/new?merge_request%5Bsource_branch%5D=<branch>`
   (user sets source project to `${GL_USER}/open-spec-mado` and target to `anankuma/open-spec-mado` `main`).

6. Continue to step 8 — report **MR fallback** success (include MR URL when created).

### 8. Cleanup and report

```bash
rm -rf "$WORK_DIR" "$STAGED_DIR"
```

## Output On Success (direct `main` push)

```
## Metrics Published

**Change:** <change-name>
**Operator:** <operator folder>
**Method:** direct push
**Commit:** <short-sha> on anankuma/open-spec-mado main
**Files published:**
- data/open-spec-matrics/operators/<operator>/<dev-filename>
- data/open-spec-matrics/operators/<operator>/QE/<qe-filename>   (if included)
**Tree:** https://gitlab.cee.redhat.com/anankuma/open-spec-mado/-/tree/main/data/open-spec-matrics/operators/<operator>
```

## Output On Success (MR fallback)

```
## Metrics Published (MR fallback)

**Change:** <change-name>
**Operator:** <operator folder>
**Method:** fork branch + merge request (upstream main push denied)
**Branch:** <GL_USER>/open-spec-mado:`<branch>`
**Files published:** (same paths as above, on branch)
**MR:** <MR URL>
```

Remind: a maintainer must **merge the MR** for data to land on upstream `main`. Merging does not
alone refresh the live dashboard — the dashboard owner may still trigger data processing.

## Guardrails

- **Step 0 (GitLab auth) is mandatory** — verify `glab api user` before cloning.
- **Pre-push guard (step 2) is mandatory** — productivity and Jira metadata must pass;
  no interim/partial publish to `main`.
- **Never ask the user to paste `GITLAB_TOKEN` in chat** — export in terminal only.
- **Never echo, log, or write `GITLAB_TOKEN`** to any file or command output.
- **Never invent metrics.** Publish telemetry from staging copies that differ from source
  **only** by the `jira_epic_name` ← `jira_task_name` fallback when epic was empty.
- **`metrics-report.json` is required** — QE-only publish is not supported.
- **Use a single atomic commit** covering dev + QE files in one push.
- **Prefer direct `main` push** to `anankuma/open-spec-mado`. If upstream push is denied,
  **automatically fall back** to fork branch + MR (step 6b); do not re-validate or alter staged JSON.
- **This command never merges the MR** — maintainer merge is required after fallback.
- **Do not modify** the change's source `telemetry/*.json` on disk when applying epic
  fallback — only the staging copy that gets committed to GitLab.
- **If `glab` is not installed**, STOP at step 0 (`dnf install glab` or
  https://gitlab.com/gitlab-org/cli).