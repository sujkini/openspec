---
name: /opsx-ci-monitor
id: opsx-ci-monitor
category: Implementation
description: Locally monitor PR CI, classify failures, auto-fix, and address review comments
argument-hint: "[change-name] [--pr <URL>] [--dry-run] [--monitor-only] [--review]"
---

Run the **local CI monitor** after `/opsx-apply` raises a PR. By default (`phase: 3`) this runs:
1. **Analysis** — poll CI, classify failures, write report
2. **Auto-fix** — fix trivial CI failures (clone → push)
3. **Review handler** — address review comments when CI is green

**Default runtime:** local (`openspec/config.yaml → ci_monitor.runtime: local`).
Prow `oape-ci-monitor` is optional — see `openspec/ci-monitor/docs/prow-ci-operator-config.yaml`.

**Input:** Change name and/or `--pr <URL>` (at least one required to resolve a PR).

## Phase behavior (from config)

**Default:** `phase: 3` — `monitor_only: false`, `auto_fix: true`, `review_handler: true`.

| Phase | Config | Behavior |
|-------|--------|----------|
| 1 | `monitor_only: true` | Analysis only — no auto-fix |
| 2 | `auto_fix: true`, `monitor_only: false` | Analysis + auto-fix |
| 3 | `review_handler: true` | Analysis + auto-fix + review comments when CI green |

CLI flags `--monitor-only` and `--review` override config for this run only.

## Prerequisites

- `gh` authenticated (`gh auth login`)
- `jq`, `python3`, `pyyaml` (`pip install pyyaml`)
- Repo listed in `openspec/ci-monitor/config/team-repos.csv` (warn-only if missing)
- Phase 2+: token with push access to PR head branch
- Phase 3 investigate/review: `claude` CLI + GCP Vertex credentials (if enabled)

## Workflow position

```
/opsx-apply  →  /opsx-ci-monitor  →  /opsx-e2e (when CI green)
```

## Step 1 — Preflight

Read `openspec/config.yaml → ci_monitor`:

- If `enabled: false` → **STOP:** "CI monitor disabled. Set `ci_monitor.enabled: true` or use `gh pr checks` manually."
- If `runtime: prow` only → **STOP:** "CI monitor configured for Prow only. Set `runtime: local` or `both`, or use `/test oape-ci-monitor` on the PR."
- If `runtime: both` → proceed locally; note Prow may also run on PR push.

## Step 2 — Resolve PR URL

Parse user arguments: `[change-name]`, `--pr <URL>`, `--dry-run`, `--monitor-only`, `--review`.

**PR resolution order:**

1. `--pr <URL>` if provided
2. Else from `change-name` → read `openspec/changes/<name>/implementation/state.yaml`:
   - Use `phase_pr_urls` for current `current_plan_phase`, or latest non-empty URL
   - Fallback: scan `implementation-report.md` for `https://github.com/.../pull/N`

If no PR resolved → **STOP:** "No PR found. Provide `--pr <URL>` or run `/opsx-apply` first."

Extract `owner`, `repo`, `pr_number` from URL.

## Step 3 — Run local CI monitor

From the **operator repo root** (where `openspec/` lives), invoke:

```bash
ARGS=(--pr-url "<PR_URL>")
[[ -n "<change-name>" ]] && ARGS+=(--change "<change-name>")
# Pass through user flags if provided:
# --dry-run --monitor-only --review

bash openspec/ci-monitor/scripts/run-local.sh "${ARGS[@]}"
```

The wrapper:
1. Sources `load-openspec-config.sh` from `openspec/config.yaml`
2. Runs `openspec/ci-monitor/scripts/pr-agent/entrypoint.sh --mode on-demand`
3. Copies artifacts to `openspec/changes/<name>/implementation/` when `--change` is set:
   - `ci-monitor-summary.md`
   - `ci-monitor-status.json`

**Do not** set `DRY_RUN` unless the user passed `--dry-run`.

## Step 4 — Interpret results

Read `ci-monitor-summary.md` (or terminal output) and `gh pr checks`:

| CI state | Action |
|----------|--------|
| Checks still pending | Tell user to wait and re-run `/opsx-ci-monitor` |
| Checks failed | Summarize failures from report; if Phase 2 ran, note if fixes were pushed |
| Checks passed | Tell user to run `/opsx-e2e <change-name> --pr <URL>` |

## Step 5 — Next steps (always output)

```
CI monitor run complete for <PR_URL>.

Artifacts:
  openspec/changes/<name>/implementation/ci-monitor-summary.md
  openspec/changes/<name>/implementation/ci-monitor-status.json

Next:
  - CI still running or failed → re-run /opsx-ci-monitor after CI updates
  - All checks green         → /opsx-e2e <change-name> --pr <URL>
```

## Guardrails

- Never push fixes when user passed `--dry-run`
- Respect `ci_monitor.phase` and flags from config unless CLI overrides given
- When `post_pr_comment: false`, report is file-only (no GitHub comment)
- Phase 3 review handler runs only when required CI is green and `--review` or `review_handler: true`
- Re-run is manual — do not auto-loop unless user asks

## Related files

| File | Role |
|------|------|
| `openspec/config.yaml` | Phase flags, runtime |
| `openspec/ci-monitor/scripts/run-local.sh` | Local entry wrapper |
| `openspec/ci-monitor/scripts/pr-agent/entrypoint.sh` | Orchestrator |
| `openspec/ci-monitor/docs/prow-ci-operator-config.yaml` | Optional Prow setup |
