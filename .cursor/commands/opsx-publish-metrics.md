---
name: /opsx-publish-metrics
id: opsx-publish-metrics
category: Workflow
description: Publish a change's metrics-report.json and qe-metrics.json to the open-spec-mado GitLab repo as a merge request
argument-hint: "[change-name]"
---

Publish a change's telemetry (`metrics-report.json` and, if present, `qe-metrics.json`) to
[anankuma/open-spec-mado](https://gitlab.cee.redhat.com/anankuma/open-spec-mado) as a merge request:
fork the repo (if not already forked), create a branch, push the files under the correct
operator folder, and open an MR against `main`.

This is a **standalone command**, run manually whenever you want to publish — it is
NOT triggered automatically by `/opsx-archive`. Typically run once a change is fully
archived and its metrics are complete, but it also works on a live (not yet archived)
change if you want to publish interim progress.

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

2. Check existing auth:
   ```bash
   glab auth status --hostname gitlab.cee.redhat.com 2>&1
   ```

3. **If already authenticated** for `gitlab.cee.redhat.com` → skip to step 7 (git protocol).

4. **If NOT authenticated**, STOP and prompt the user (steps 4–6 and 8–9 apply only in this branch):

   ```
   Before publishing metrics, export your GitLab token in the terminal.
   Do NOT paste the token in chat.

   export GITLAB_TOKEN='your-legacy-api-access-token'

   Create a Personal Access Token (legacy API access, api scope) at:
   https://gitlab.cee.redhat.com/-/user_settings/personal_access_tokens

   Reply 'done' when exported.
   ```

5. **Do NOT proceed** until the user replies `done` or `yes`.

6. Verify the token is set (never echo or log the value):
   ```bash
   [ -n "$GITLAB_TOKEN" ] && echo "GITLAB_TOKEN is set" || echo "GITLAB_TOKEN is NOT set"
   ```
   If NOT set → STOP: "GITLAB_TOKEN is not set in this shell. Export it in the
   Cursor integrated terminal and reply 'done' again."

7. **Ask git protocol** (use **AskQuestion**):
   - **HTTPS (Recommended)** — default for token auth; clone/push via `https://gitlab.cee.redhat.com/...`
   - **SSH** — clone/push via `git@gitlab.cee.redhat.com:...` (requires SSH key configured)

   Default to **HTTPS** if the user skips or does not choose.

8. Log in non-interactively using the exported token (skip if step 3 already authenticated):
   ```bash
   glab auth login \
     --hostname gitlab.cee.redhat.com \
     --token "$GITLAB_TOKEN" \
     --git-protocol <https|ssh>
   ```

9. Verify login succeeded (always run, even if step 3 was authenticated):
   ```bash
   glab auth status --hostname gitlab.cee.redhat.com
   ```
   If verification fails → STOP with the error output. Do not continue.

10. Persist the chosen protocol for this run as `GIT_PROTOCOL` (`https` or `ssh`).

**Security guardrails for this step:**
- NEVER ask the user to paste the token in chat
- NEVER run `echo $GITLAB_TOKEN` or log the token in command output
- NEVER commit or write the token to any file

### 1. Resolve the change and locate its telemetry files

The change may already be archived (moved to `openspec/changes/archive/YYYY-MM-DD-<name>/`)
or still live (`openspec/changes/<name>/`). Check both locations, preferring the
archived one if both somehow exist:

```bash
ls openspec/changes/archive/*-<name>/telemetry/ 2>/dev/null
ls openspec/changes/<name>/telemetry/ 2>/dev/null
```

Read whichever of these exist from the resolved directory:
- `telemetry/metrics-report.json` (development metrics)
- `telemetry/qe-metrics.json` (QE/E2E metrics — only if `/opsx-e2e` ran for this change)

**If neither file exists:** STOP — "No telemetry found for `<name>`. Run `/opsx-apply`
(and `/opsx-archive`) first." Do not proceed.

### 2. Check completeness (warn, don't block)

- If `metrics-report.json` exists: check `report_status.complete`.
- If `qe-metrics.json` exists: check `qe_report_status.complete`.

If either is `false`, warn the user:
**"⚠ `<file>` is marked incomplete (`report_status.complete: false` — missing
`<missing_fields>`). This usually means `/opsx-archive` hasn't fully run yet.
Publish anyway?"** — proceed only if the user confirms.

### 3. Determine the operator folder name

Read `operator_name` from `metrics-report.json` (top-level field, set automatically
by `telemetry/report.py` from `git remote get-url origin` at telemetry-generation time).

- **If `metrics-report.json` exists:** use its `operator_name` field.
- **If only `qe-metrics.json` exists** (no dev metrics were ever generated for this
  change): run `git remote get-url origin` directly and derive the name the same way
  (strip `.git`, take the last path segment).

**Normalize** to the dashboard repo's folder convention — lowercase, hyphens → underscores:
```
cert-manager  → cert_manager
ZTWIM         → ztwim
must-gather   → must_gather
```

If the normalized name doesn't match one of the dashboard's existing operator folders,
**that's fine — proceed anyway.** The push will implicitly create the new folder.

### 4. Determine filenames

Read `jira_key` from `metrics-report.json → jira_task_link` (extract the trailing
path segment) or from `inputs/jira.yaml → jira_key` if the change is still live.

Read `codegen_mode` from `openspec/config.yaml → flags.codegen_mode` (default: `direct`).

ASK the user: **"What model was primarily used for this run? (e.g. `composer-2.5`,
`sonnet-5`, `opus`) — press Enter to skip."**
- If provided: `model_slug` = the answer, lowercased, spaces → hyphens.
- If skipped: omit the model segment entirely from the filename.

Build target filenames:

| File | Target path |
|------|-------------|
| `metrics-report.json` | `data/open-spec-matrics/operators/<operator>/<JIRA_KEY>-<codegen_mode>[-<model_slug>]-metrics-report.json` |
| `qe-metrics.json` | `data/open-spec-matrics/operators/<operator>/QE/<JIRA_KEY>-qe-metrics.json` |

Only include a row for a file that actually exists (from step 1).

### 5. Fork and clone the dashboard repo

```bash
GITLAB_UPSTREAM="https://gitlab.cee.redhat.com/anankuma/open-spec-mado.git"
WORK_DIR="$(mktemp -d)"
```

1. **Fork** (if not already forked):
   ```bash
   glab repo fork anankuma/open-spec-mado --clone=false 2>/dev/null || true
   ```
   If `glab` is not available, instruct the user:
   "Fork https://gitlab.cee.redhat.com/anankuma/open-spec-mado via the GitLab UI, then re-run this command."

2. **Determine fork URL** from `GIT_PROTOCOL` chosen in step 0:
   ```bash
   GL_USER=$(glab auth status --hostname gitlab.cee.redhat.com 2>&1 | grep -oP 'Logged in to .* as \K\S+')
   ```
   Do NOT fall back to `git config user.name` — if `GL_USER` is empty, STOP (auth broken).

   | `GIT_PROTOCOL` | `FORK_URL` |
   |----------------|------------|
   | `https` (default) | `https://gitlab.cee.redhat.com/${GL_USER}/open-spec-mado.git` |
   | `ssh` | `git@gitlab.cee.redhat.com:${GL_USER}/open-spec-mado.git` |

3. **Clone and create branch:**
   ```bash
   git clone --depth 1 "$FORK_URL" "$WORK_DIR/open-spec-mado"
   cd "$WORK_DIR/open-spec-mado"
   git remote add upstream "$GITLAB_UPSTREAM" 2>/dev/null || true
   git fetch upstream main
   git checkout -b "metrics/<jira-key-lowercase>-$(date +%Y%m%d-%H%M)" upstream/main
   ```

### 6. Copy files and commit

```bash
OPERATOR_DIR="data/open-spec-matrics/operators/<operator>"
mkdir -p "$OPERATOR_DIR"
cp <path-to-metrics-report.json> "$OPERATOR_DIR/<dev-filename>"

# Only if qe-metrics.json exists:
mkdir -p "$OPERATOR_DIR/QE"
cp <path-to-qe-metrics.json> "$OPERATOR_DIR/QE/<qe-filename>"

git add "$OPERATOR_DIR/"
git commit -m "Add <JIRA_KEY> metrics for <operator>"
```

### 7. Push branch (always attempt)

```bash
git push -u origin "metrics/<branch-name>"
```

If push fails → STOP with error. Do not attempt MR creation.

### 7b. Open merge request (attempt — degrade gracefully on failure)

Try to open an MR against the upstream repo:
```bash
glab mr create \
  --hostname gitlab.cee.redhat.com \
  --repo anankuma/open-spec-mado \
  --source-branch "metrics/<branch-name>" \
  --target-branch main \
  --title "Add <JIRA_KEY> metrics — <operator>" \
  --description "$(cat <<'EOF'
## Metrics for <JIRA_KEY> (<operator>)

| Metric | Value |
|--------|-------|
| Story points delivered | <productivity_metrics.story_points_delivered, if present> |
| Time saved | <productivity_metrics.time_saved_hours> hours (est.) |
| Satisfaction | <productivity_metrics.satisfaction_rating>/5 |
| Total tokens | <global_health.total_tokens_consumed> |
| Estimated cost | $<global_health.estimated_cost_usd> |
| QE story points | <qe productivity_metrics.story_points_delivered, if included> |
| QE time saved | <qe productivity_metrics.time_saved_hours> hours (if included) |
| QE satisfaction | <qe productivity_metrics.satisfaction_rating>/5 (if included) |

Generated by `/opsx-publish-metrics`.
EOF
)"
```

**If MR creation fails** (auth, permissions, cross-project, or any `glab` error):
- Do NOT fail the whole command — the branch push (step 7) is the critical part
- Output partial success:

```
## Metrics Published (MR manual step required)

Branch pushed: https://gitlab.cee.redhat.com/<GL_USER>/open-spec-mado/-/tree/metrics/<branch-name>

MR could not be created automatically (<error summary>).
Create the MR manually:
https://gitlab.cee.redhat.com/anankuma/open-spec-mado/-/merge_requests/new?merge_request%5Bsource_branch%5D=metrics/<branch-name>&merge_request%5Btarget_branch%5D=main
```

Fall back to GitLab API only if `glab mr create` fails and `$GITLAB_TOKEN` is set:
```bash
curl --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.cee.redhat.com/api/v4/projects/${GL_USER}%2Fopen-spec-mado/merge_requests" \
  --data-urlencode "source_branch=metrics/<branch-name>" \
  --data-urlencode "target_branch=main" \
  --data-urlencode "title=Add <JIRA_KEY> metrics — <operator>" \
  --data-urlencode "description=<summary table>"
```
If API also fails → keep the manual MR URL from above.

### 8. Cleanup and report

```bash
rm -rf "$WORK_DIR"
```

Output the MR URL and remind the user:

**"MR opened: `<MR URL>`. The dashboard repo owner needs to merge this MR for the data to appear."**

## Output On Success

```
## Metrics Published

**Change:** <change-name>
**Operator:** <operator folder>
**Files published:**
- data/open-spec-matrics/operators/<operator>/<dev-filename>          (if included)
- data/open-spec-matrics/operators/<operator>/QE/<qe-filename>        (if included)
**Branch:** <your-username>:metrics/<branch-name>
**MR:** <MR URL>
```

## Output On Partial Success (branch pushed, MR manual)

```
## Metrics Published (MR manual step required)

**Change:** <change-name>
**Operator:** <operator folder>
**Files published:**
- data/open-spec-matrics/operators/<operator>/<dev-filename>          (if included)
- data/open-spec-matrics/operators/<operator>/QE/<qe-filename>        (if included)
**Branch:** https://gitlab.cee.redhat.com/<GL_USER>/open-spec-mado/-/tree/metrics/<branch-name>
**MR:** Create manually — see link above
```

## Guardrails

- **Step 0 (GitLab auth) is mandatory** — do not fork, clone, push, or open an MR
  until `glab auth status --hostname gitlab.cee.redhat.com` succeeds.
- **Never ask the user to paste `GITLAB_TOKEN` in chat** — export in terminal only.
- **Never echo, log, or write `GITLAB_TOKEN`** to any file or command output.
- **Default git protocol is HTTPS** — use SSH only when the user explicitly chooses it in step 0.
- **Never invent metrics.** Only publish the raw JSON exactly as written by
  `telemetry/report.py` / `telemetry/qe_metrics.py` — do not summarize, reformat,
  round, or edit values before pushing.
- **Do not publish if neither file exists** for the resolved change — stop with a
  clear error (step 1).
- **Warn but don't hard-block on incompleteness** (step 2) — unlike `/opsx-archive`,
  this command is not a compliance gate; the user may legitimately want to publish
  partial/interim data.
- **Required-field parity with the target repo:** ensure non-empty `jira_task_name` and
  `jira_task_link` on every JSON file pushed. Both `metrics-report.json` (via
  `telemetry/jira_metadata.py`) and `qe-metrics.json` already populate these —
  do not push a file where either is empty; if empty, tell the user to ensure
  `inputs/jira.yaml` has `jira_key`/`jira_summary` set, then regenerate the report.
- **Use a single atomic commit** covering both files — do not make two separate
  commits/MRs for one change.
- **This command never merges the MR** — that requires the target repo owner's action.
- **Prefer `glab` CLI** for fork/MR operations. If MR creation fails after a
  successful push, output the manual MR URL — do not discard the pushed branch.
- **If `glab` is not installed**, STOP at step 0 and tell the user to install glab
  (`dnf install glab` or https://gitlab.com/gitlab-org/cli).
