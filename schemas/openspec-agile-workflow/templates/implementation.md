# Implementation Phase Log

**Change**: [CHANGE_NAME]
**Jira**: [JIRA_KEY]
**Fork**: [FORK_REPO_URL]
**Branch**: [FEATURE_BRANCH]
**Started**: [DATE]

Append one section per **approved task** during `/opsx:apply`. OAPE commands run
task-by-task; code changes go to the fork working copy.

---

## Task: [TASK_ID] — [TASK_TITLE]

**Phase**: [PHASE_NAME]
**Status**: [Approved | In Progress | Rejected]
**Agent**: [ASSIGNED_AGENT]

### OAPE Commands Executed

| Command | Args | Outcome |
|---------|------|---------|
| /oape:api-generate | --design-doc …/design-bundle.md | Success |

### Files Touched

- `relative/path/to/file`

### Test Results

| Test | Result | Notes |
|------|--------|-------|
| make test | PASSED | |

### Deviations

- [description and rationale — omit section when none]

---

## Phase Log Notes

- Tasks execute in §2 Linear Execution Order; respect §1 DAG.
- Design bundle: `implementation/design-bundle.md` (regenerated per task, scoped to one Task ID).
- **User approval after every task** before advancing to the next.
- On reject: update REVISION FEEDBACK in design bundle; re-run the current task only.
