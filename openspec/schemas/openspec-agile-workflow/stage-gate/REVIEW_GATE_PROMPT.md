# Pre-PR Code Review Gate — `/opsx-apply` phase boundary

Run an automated **Principal Engineer level code review** on accumulated code changes
in the fork working copy after all tasks complete (per phase or all tasks), **auto-fix
issues**, then present results for **user approval** before the PR prompt.

Paths below are **relative to the schema root** (`openspec/schemas/openspec-agile-workflow/` when installed).

## Mandatory sequence

```
1. Read config → review flags (review_gate, review_auto_fix, etc.)
2. Determine diff scope (base_ref, head_ref, jira_key)
3. Run /oape:review engine → capture JSON report
4. IF issues AND review_auto_fix → auto-fix loop (max review_max_fix_rounds)
5. Write review-report.md
6. Update state.yaml review block
7. Present results with verdict, scorecard, and issue summary
8. Approval gate (respects auto_approve + review_block_on_critical)
```

| Step | User approval allowed? |
|------|------------------------|
| 1–6 | **No** — complete review + fix loop first |
| 7–8 | **Yes** — present full results, then ask |

## Step 1 — Read review configuration

Read `openspec/config.yaml` → `flags`:

```yaml
review_gate: true               # Skip entire gate if false
review_auto_fix: true           # Auto-apply fixes
review_max_fix_rounds: 2        # Max iterations
review_block_on_critical: true  # Block PR on CRITICAL
```

**IF `review_gate` is `false`:** Skip the entire review gate. Log: "Review gate disabled
(flags.review_gate = false). Proceeding to PR prompt." Proceed to PR prompt directly.

## Step 2 — Determine diff scope

Read `inputs/jira.yaml`:
- `jira_key` — for Jira intent matching in the review
- `feature_branch` — current implementation branch
- `local_clone_path` — fork working directory

Determine `base_ref`:
```bash
# Preferred: fork default branch
BASE_REF=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/||')
# Fallback
BASE_REF="${BASE_REF:-origin/main}"
```

Compute diff statistics for context:
```bash
git diff ${BASE_REF}...HEAD --stat
git diff ${BASE_REF}...HEAD --name-only
```

## Step 3 — Run /oape:review engine

Set `state.yaml → review.status: running`.

Invoke the `/oape:review` engine (see `.cursor/commands/review.md`):
- Pass `jira_key` as the ticket ID argument
- Pass `base_ref` as the base ref argument
- Capture the **full JSON report** output including:
  - `summary.verdict` — "Approved" or "Changes Requested"
  - `summary.rating` — 1-10
  - `summary.simplicity_score` — 1-10
  - `logic_verification.jira_intent_met` — boolean
  - `logic_verification.missing_edge_cases` — array
  - `issues[]` — array of issue objects

Parse the JSON report. Count issues by severity:
- `critical_count` = issues where `severity == "CRITICAL"`
- `warning_count` = issues where `severity == "WARNING"`
- `info_count` = issues where `severity == "INFO"`

Update `state.yaml`:
```yaml
review:
  status: running
  issues_total: <total issue count>
  review_base_ref: <base_ref>
  last_reviewed_at: <ISO8601>
```

**IF `issues` array is empty AND `verdict` is "Approved":**
Set `review.status: passed`, `review.verdict: Approved`. Skip to Step 5.

## Step 4 — Auto-fix loop

**IF `review_auto_fix` is `false`:** Skip auto-fix. Proceed to Step 5 with all
issues as remaining.

**IF `review_auto_fix` is `true` AND issues exist:**

Set `state.yaml → review.status: fixing`.

```
FOR round IN 1..review_max_fix_rounds:
  IF no remaining issues: BREAK

  4a. Invoke /oape:implement-review-fixes with the current JSON report
      → Captures fix summary (applied count, skipped count)

  4b. Re-verify the codebase:
      go build ./...
      go vet ./...
      go test ./... (or scoped to changed packages)
      IF build fails: revert the failing fix, continue

  4c. Re-run /oape:review to check remaining issues
      → Capture new JSON report
      → Update issue counts

  4d. Update state.yaml:
      review.fix_rounds: <round>
      review.issues_fixed: <cumulative fixed count>
      review.issues_remaining: <remaining count>

  IF remaining issues == 0: BREAK
```

After the loop, compute final tallies:
- `issues_fixed` = `issues_total` - current `issues_remaining`

## Step 5 — Write review report

Write `openspec/changes/<change>/implementation/review-report.md` using the
template at `templates/review-report-template.md`.

Populate all template fields from the review JSON report, fix summary, and
verification results.

Update `state.yaml`:
```yaml
review:
  report_path: openspec/changes/<change>/implementation/review-report.md
```

## Step 6 — Update state

Determine the final review outcome:

```yaml
review:
  status: <passed if verdict=Approved and no criticals, else approval>
  verdict: <from JSON report>
  blocked_by_critical: <true if CRITICAL issues remain AND review_block_on_critical>
```

## Step 7 — Present review results

```
## Pre-PR Code Review Results

**Verdict:** {Approved | Changes Requested}
**Rating:** {rating}/10 | **Simplicity:** {simplicity}/10

### Summary
| Metric | Count |
|--------|-------|
| Total issues | {N} |
| Auto-fixed | {M} |
| Remaining | {R} |
| Fix rounds | {rounds} |

### Issues by Severity
| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| CRITICAL | {n} | {m} | {r} |
| WARNING  | {n} | {m} | {r} |
| INFO     | {n} | {m} | {r} |

### Remaining Issues (if any)
| # | Severity | Module | File:Line | Description |
...

### Files Touched by Auto-Fix
- path/to/file — brief description

### Verification After Fixes
| Command | Exit Code | Result |
...
```

**IF `review_block_on_critical` AND CRITICAL issues remain:**
Add warning callout:
```
⚠️  {N} CRITICAL issue(s) remain unresolved. PR creation is blocked.
    Resolve these issues or override with explicit approval.
```

## Step 8 — Approval gate

**Determine approval mode:**

1. **Clean review (verdict = Approved, no remaining issues):**
   - IF `auto_approve` is `true`: auto-approve. Log: "Review gate auto-approved (clean review)."
   - IF `auto_approve` is `false`: ASK: "Pre-PR review passed (Approved, 0 issues). Proceed to PR? (Yes / No)"

2. **Issues remain but no CRITICALs:**
   - IF `auto_approve` is `true`: auto-approve. Log: "Review gate auto-approved ({R} non-critical issues remaining)."
   - IF `auto_approve` is `false`: ASK: "Pre-PR review: {verdict}. {N} issues found, {M} auto-fixed, {R} remaining (no CRITICALs). Approve and proceed to PR? (Approve / Reject with feedback)"

3. **CRITICAL issues remain AND `review_block_on_critical` is `true`:**
   - **ALWAYS prompt** regardless of `auto_approve`:
     ASK: "{C} CRITICAL issue(s) remain unresolved. PR creation is blocked by policy (review_block_on_critical). Options:
     1. Re-review with feedback (attempt to address CRITICALs)
     2. Override and proceed to PR anyway (records override in review report)
     3. Stop — address issues manually"
   - On **Override**: record override reason in review-report.md, set `review.blocked_by_critical: false`, proceed to PR prompt.
   - On **Re-review**: increment `review_feedback_rounds`, re-run from Step 3.
   - On **Stop**: set `review.status: failed`, YIELD.

**On approve (any path):**
- Set `state.yaml → review.status: passed`
- Proceed to PR prompt (existing Step 6b/5 in `/opsx-apply`)

**On reject with feedback:**
- Increment `review.review_feedback_rounds`
- IF `review_feedback_rounds > 2`: HALT. "Max review feedback rounds reached. Address remaining issues manually."
- ELSE: incorporate feedback context, re-run from Step 3.

## Guardrails

- **Never** skip verification after auto-fixes
- **Never** modify approved upstream artifacts (specs.md, plan.md, tasks.md) during review
- **Never** auto-approve when CRITICAL issues remain and `review_block_on_critical` is `true`
- **Always** persist review results to state.yaml and review-report.md
- **Always** re-verify (`go build`, `go vet`) after every auto-fix round
- Review operates on the **fork working copy** only — never touches upstream
- Auto-fix budget: `review_max_fix_rounds` (default: 2) — shared with user re-review rounds
