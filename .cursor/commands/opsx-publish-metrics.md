---
name: /opsx-publish-metrics
id: opsx-publish-metrics
category: Workflow
description: Publish a change's metrics-report.json and qe-metrics.json to the open-spec-dashboard repo as a PR
argument-hint: "[change-name]"
---

Publish a change's telemetry (`metrics-report.json` and, if present, `qe-metrics.json`) to
[anandkuma77/open-spec-dashboard](https://github.com/anandkuma77/open-spec-dashboard) as a pull request:
fork the repo (if not already forked), branch, push the two files under the correct
operator folder, and open a PR against `main`.

This is a **standalone command**, run manually whenever you want to publish — it is
NOT triggered automatically by `/opsx-archive`. Typically run once a change is fully
archived and its metrics are complete, but it also works on a live (not yet archived)
change if you want to publish interim progress.

**Input**: Optionally specify a change name. If omitted, check conversation context;
if still ambiguous, list both active changes (`openspec list --json`) and archived
changes (`ls openspec/changes/archive/`) and let the user pick via **AskQuestion**.

## Steps

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

If the normalized name doesn't match one of the dashboard's existing operator folders
(`cert_manager`, `ztwim`, `sscsi`, `must_gather`, `eso`), **that's fine — proceed anyway.**
`push_files` (step 6) will implicitly create the new folder (and its `QE/` subfolder,
if needed) as part of the commit; GitHub does not require directories to pre-exist.

### 4. Determine filenames

Read `jira_key` from `metrics-report.json → jira_task_link` (extract the trailing
path segment) or from `inputs/jira.yaml → jira_key` if the change is still live.

Read `codegen_mode` from `openspec/config.yaml → flags.codegen_mode` (default: `direct`).

ASK the user: **"What model was primarily used for this run? (e.g. `composer-2.5`,
`sonnet-5`, `opus`) — press Enter to skip."**
- If provided: `model_slug` = the answer, lowercased, spaces → hyphens.
- If skipped: omit the model segment entirely from the filename.

Build target filenames (matching the existing convention on the dashboard repo, e.g.
`CM-830-ai-helpers-composer-2.5-metrics-report.json`):

| File | Target path |
|------|-------------|
| `metrics-report.json` | `data/open-spec-matrics/operators/<operator>/<JIRA_KEY>-<codegen_mode>[-<model_slug>]-metrics-report.json` |
| `qe-metrics.json` | `data/open-spec-matrics/operators/<operator>/QE/<JIRA_KEY>-qe-metrics.json` |

Only include a row for a file that actually exists (from step 1).

### 5. Fork and branch (via the `user-github` MCP server)

1. Call `get_me` to get the authenticated GitHub username (`<fork-owner>`).
2. Call `fork_repository` with `owner: "anandkuma77"`, `repo: "open-spec-dashboard"`.
   This is idempotent — if a fork already exists, GitHub returns it rather than erroring.
   **Note:** forks can take a few seconds to become writable after creation; if
   `create_branch` in the next step fails with a "not found" style error immediately
   after a fresh fork, wait briefly and retry once.
3. Call `create_branch` with `owner: "<fork-owner>"`, `repo: "open-spec-dashboard"`,
   `branch: "metrics/<jira-key-lowercase>-<YYYYMMDD-HHMM>"`, `from_branch: "main"`.
   (The timestamp suffix avoids branch-name collisions across repeated publishes.)

### 6. Push the files

Call `push_files` with `owner: "<fork-owner>"`, `repo: "open-spec-dashboard"`,
`branch: "<branch from step 5>"`, and a `files` array containing each target path
from step 4 with its raw JSON content (byte-for-byte from the local file — do NOT
reformat or re-summarize the JSON).

`message`: `"Add <JIRA_KEY> metrics for <operator>"` (mention both dev and QE if both
are included).

### 7. Open the pull request

Call `create_pull_request` with:
- `owner: "anandkuma77"`, `repo: "open-spec-dashboard"` (the **upstream** repo, not the fork)
- `head: "<fork-owner>:<branch from step 5>"`
- `base: "main"`
- `title`: `"Add <JIRA_KEY> metrics — <operator>"`
- `body`: a short summary table, e.g.:
  ```markdown
  ## Metrics for <JIRA_KEY> (<operator>)

  | Metric | Value |
  |--------|-------|
  | Story points delivered | <productivity_metrics.story_points_delivered, if present> |
  | Time saved | <productivity_metrics.time_saved_hours> hours (est.) |
  | Total tokens | <global_health.total_tokens_consumed> |
  | Estimated cost | $<global_health.estimated_cost_usd> |
  | QE story points | <qe_feedback.story_points_delivered, if qe-metrics.json included> |
  | QE time saved | <qe_feedback.time_saved_pct>% (if included) |

  Generated by `/opsx-publish-metrics`.
  ```

### 8. Report next steps

Output the PR URL and remind the user:

**"PR opened: `<PR URL>`. Note: the live dashboard reads from `data/processed/`,
which is NOT regenerated automatically on merge — after this PR is merged, the
dashboard repo owner needs to manually trigger the `Generate Processed Metrics`
GitHub Action (`workflow_dispatch`) for the data to appear on the live site."**

## Output On Success

```
## Metrics Published

**Change:** <change-name>
**Operator:** <operator folder>
**Files published:**
- data/open-spec-matrics/operators/<operator>/<dev-filename>          (if included)
- data/open-spec-matrics/operators/<operator>/QE/<qe-filename>        (if included)
**Branch:** <fork-owner>:<branch>
**PR:** <PR URL>

Merging this PR alone will NOT update the live dashboard — the repo owner must
manually run the "Generate Processed Metrics" workflow afterward.
```

## Guardrails

- **Never invent metrics.** Only publish the raw JSON exactly as written by
  `telemetry/report.py` / `telemetry/qe_metrics.py` — do not summarize, reformat,
  round, or edit values before pushing.
- **Do not publish if neither file exists** for the resolved change — stop with a
  clear error (step 1).
- **Warn but don't hard-block on incompleteness** (step 2) — unlike `/opsx-archive`,
  this command is not a compliance gate; the user may legitimately want to publish
  partial/interim data.
- **Required-field parity with the target repo:** the target repo's CI
  (`validate-metrics-json.yml`) requires non-empty `jira_task_name` and
  `jira_task_link` on every JSON file pushed. Both `metrics-report.json` (via
  `telemetry/jira_metadata.py`) and `qe-metrics.json` already populate these —
  do not push a file where either is empty; if empty, tell the user to ensure
  `inputs/jira.yaml` has `jira_key`/`jira_summary` set, then regenerate the report.
- **Use `push_files` for a single atomic commit** covering both files — do not
  make two separate commits/PRs for one change.
- **`head` for `create_pull_request` must be `"<fork-owner>:<branch>"`**, not just
  `"<branch>"` — this is a cross-repo (fork → upstream) PR.
- **This command never merges the PR or triggers the dashboard's processing
  workflow** — those require the target repo owner's action, out of scope here.
