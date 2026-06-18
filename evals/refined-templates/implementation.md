# Implementation Phase Log

**Change**: [CHANGE_NAME]
**Jira**: [JIRA_KEY]
**Fork**: [FORK_REPO_URL]
**Branch**: [FEATURE_BRANCH]
**Started**: [DATE]

Append one section per **approved task**. Each task also gets
`implementation/task-reports/[TASK_ID].md`. Code changes go to the fork — not this file.

---

## Task: [TASK_ID] — [TASK_TITLE]

**Phase**: [PHASE_NAME]
**Status**: Approved
**Agent**: [ASSIGNED_AGENT]
**OAPE Command**: [command or manual]
**Task report**: [implementation/task-reports/TASK_ID.md]

### Code Generation Eval

| Metric | Value |
|--------|-------|
| Overall score | [N]% |
| Cases pass | [N]/[M] |
| Refinement rounds | [0–2] |

### Files Touched

- `relative/path/to/file`

### Test Results

| Test | Result | Notes |
|------|--------|-------|
| make test | PASSED | |

### Deviations

- [Task ID + rationale — omit when none]

---

## Reconciler guardrails (code generation — not logged in this file)

When implementing controller-runtime reconcilers (addons, user-defined NetworkPolicy, SSA-managed resources):

- **Unified manager wiring:** register addon controllers in `setup_manager.go` via `Enable<Name>` flags and
  shared `ctrl.Manager` — never create a separate Manager or isolated cache per addon (driver: CM-735).
- **Compare before update:** use equality / `modified()` checks — skip `client.Apply` or `Patch` when desired
  state matches current (prevents hot-loop reconcile; driver: CM-763 pattern).
- **Static managed resources (library-go):** drift in operator-owned fields must be reverted on reconcile
  (driver: CM-758 pattern).
- **User-defined resources:** register `Watches()` on managed GVK; delete events must trigger recreate via
  watch/informer — verify in e2e (driver: CM-764 pattern).
- **Status conditions:** call `updateStatus()` / `SetCondition()` for `Ready` when operand healthy and
  `Degraded` on failure — pair with e2e assertion on `.status.conditions[?(@.type=='Ready')]` (driver: CM-546).
- **Limited teardown on CR delete:** on deletion timestamp, stop reconcile and emit warning event — do NOT
  implement full operand cleanup unless task payload explicitly requires it (driver: EP non-goals / PAT-002).
- Log intentional deviations from task payloads under **Deviations** above with Task ID and rationale.

## Phase Log Notes

- Per-task flow: OAPE → verify → code evals → refine code → user code approval → task report.
- On reject: REVISION FEEDBACK in design bundle; re-run current task only.
