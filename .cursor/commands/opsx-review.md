---
name: /opsx-review
id: opsx-review
category: Workflow
description: Pre-PR code review gate — runs /oape:review on accumulated changes, auto-fixes issues, presents for approval
argument-hint: [change-name] [--phase N] [--base-ref REF]
---

Run an automated pre-PR code review on the accumulated code changes in the fork working copy.
Can be invoked standalone or auto-triggered from `/opsx-apply` at phase/completion boundary.

Read `config.yaml → flags.auto_approve` at the start of every invocation.

**Input**: Optional change name, `--phase N` to scope review, `--base-ref REF` to override base.

## Schema Reference

Read and follow **`{schema_root}/stage-gate/REVIEW_GATE_PROMPT.md`** Steps 1–8 exactly.
This is the single source of truth for the review gate flow.

Key schema paths:
- Review gate schema: `schema.yaml → code_review_gate`
- Review gate prompt: `{schema_root}/stage-gate/REVIEW_GATE_PROMPT.md`
- Review report template: `{schema_root}/templates/review-report-template.md`
- Review engine: `.cursor/commands/review.md` (`/oape:review`)
- Auto-fixer: `.cursor/commands/implement-review-fixes.md` (`/oape:implement-review-fixes`)
- State file: `openspec/changes/<name>/implementation/state.yaml`

## PREFLIGHT LOG — MANDATORY

After reading config, print this block before any review execution:

```
Review Preflight:
  review_gate: {true|false}
  review_auto_fix: {true|false}
  review_max_fix_rounds: {N}
  review_block_on_critical: {true|false}
  auto_approve: {true|false}
  change: {change_name}
  phase: {N or all}
  local_clone_path: {from jira.yaml}
  feature_branch: {from jira.yaml}
  base_ref: {computed base ref}
  jira_key: {from jira.yaml}
```

If preflight is not printed, the run is non-compliant.

## Steps

### 1. Resolve context

1. Select change (`openspec list --json` if name not given).
2. Read `openspec/changes/<name>/inputs/jira.yaml`:
   - `jira_key` — ticket ID for intent matching
   - `local_clone_path` — fork working directory
   - `feature_branch` — implementation branch
3. Read `openspec/config.yaml` → review flags.
4. `cd local_clone_path`; verify `feature_branch` is checked out.

**IF `review_gate` is `false`:**
Output: "Review gate is disabled (flags.review_gate = false). Enable it in config.yaml to use /opsx-review."
STOP.

### 2. Determine diff scope

```bash
# Base ref: from --base-ref arg, or fork default branch
if [[ -n "$BASE_REF_ARG" ]]; then
  BASE_REF="$BASE_REF_ARG"
else
  BASE_REF=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/||')
  BASE_REF="${BASE_REF:-origin/main}"
fi

# Verify base ref exists
git rev-parse --verify "$BASE_REF" 2>/dev/null || { echo "Base ref $BASE_REF not found"; exit 1; }

# Diff stats for context
git diff ${BASE_REF}...HEAD --stat
git diff ${BASE_REF}...HEAD --name-only
```

### 3. Initialize or read state

Read `openspec/changes/<name>/implementation/state.yaml`.

If `review` block is missing, initialize from template (see schema `code_review_gate.state_tracking`).

Update state:
```yaml
review:
  status: running
  review_base_ref: <base_ref>
  last_reviewed_at: <ISO8601>
```

Write state.yaml.

### 4. Telemetry — signal review start

```bash
python -m openspec.telemetry.auto on-review-start --change "<name>"
```
Add `--phase <N>` only when invoked with `--phase` or from phase-iterative `/opsx-apply`.

### 5. Run /oape:review

Follow **REVIEW_GATE_PROMPT.md Step 3** exactly:

1. Invoke `/oape:review <jira_key> <base_ref>` — capture JSON report.
2. Parse verdict, issues[], scores.
3. IF issues found AND `review_auto_fix` is true:
   - Run auto-fix loop (REVIEW_GATE_PROMPT.md Step 4).
   - Max `review_max_fix_rounds` iterations.
4. Write `implementation/review-report.md` from template.
5. Update all `state.yaml → review` fields.

### 6. Present results

Follow **REVIEW_GATE_PROMPT.md Step 7** — present the full review summary:
- Verdict, rating, simplicity score
- Issue counts by severity (found / fixed / remaining)
- Remaining issues table
- Files touched by auto-fix
- Verification results after fixes

### 7. Approval gate

Follow **REVIEW_GATE_PROMPT.md Step 8** — determine approval mode:

- **Clean review:** auto-approve if `auto_approve` is true, else prompt.
- **Non-critical issues remain:** auto-approve if `auto_approve` is true, else prompt.
- **CRITICAL issues remain + block_on_critical:** ALWAYS prompt (override / re-review / stop).

### 8. Telemetry — signal review complete

```bash
python -m openspec.telemetry.auto on-review-complete \
  --change "<name>" \
  --verdict "<verdict>" \
  --issues <total> \
  --fixed <fixed> \
  --remaining <remaining>
```
Add `--phase <N>` when applicable.

### 9. Post-review

**IF invoked standalone** (not from `/opsx-apply`):
- Output: "Review complete. Verdict: {verdict}. Run `/opsx-apply` to continue with PR creation."
- STOP.

**IF invoked from `/opsx-apply`** (review gate in step 6a):
- Return control to `/opsx-apply` for PR prompt.

## Guardrails

- **Read config FIRST** — review_gate, review_auto_fix, auto_approve
- **Mandatory preflight log** — non-compliant without it
- **Never** modify approved upstream artifacts (specs, plan, tasks)
- **Never** auto-approve when CRITICALs remain and `review_block_on_critical` is true
- **Always** persist results to state.yaml and review-report.md
- **Always** re-verify after auto-fixes
- Review operates on **fork working copy** only
- **No background sub-agents** — review runs in the main agent session
