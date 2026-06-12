# Implementation Phase Log

**Change**: [CHANGE_NAME]
**Jira**: [JIRA_KEY]
**Fork**: [FORK_REPO_URL]
**Branch**: [FEATURE_BRANCH]
**Started**: [DATE]

Append one section per approved phase during `/opsx:apply`. Code changes go to the fork working copy — not this file.

---

## Phase: [PHASE_NAME]

**Status**: [Approved | In Progress | Rejected]
**Tasks**: [T1_1, T1_2, …]

### Files Touched

- `relative/path/to/file`

### Test Results

| Test | Result | Notes |
|------|--------|-------|
| [test name] | PASSED / FAILED / SKIPPED | [brief detail] |

### Deviations

- **Task ID**: [description and rationale — omit section when none]

---

## Reconciler guardrails (code generation — not logged in this file)

When implementing controller-runtime reconcilers (addons, user-defined NetworkPolicy, SSA-managed resources):

- **Compare before update:** use equality / `modified()` checks — skip `client.Apply` or `Patch` when desired
  state matches current (prevents hot-loop reconcile; driver: CM-763 pattern).
- **Static managed resources (library-go):** drift in operator-owned fields must be reverted on reconcile.
- **User-defined resources:** delete events must trigger recreate via watch/informer — verify in e2e.
- Log intentional deviations from task payloads under **Deviations** above with Task ID and rationale.

## Phase Log Notes

- Phases execute in dependency order from tasks.md §1–§2.
- Each phase requires user approval before advancing.
- On reject: re-generate FILE OPERATIONS, re-apply, repeat until approved.
