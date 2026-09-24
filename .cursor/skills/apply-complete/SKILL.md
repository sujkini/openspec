# Apply Complete

Finalize the implementation after all tasks (one-shot) or all phases (phase-iterative) are done.

## Steps

### 1. Telemetry

```bash
python -m openspec.telemetry.auto on-apply-complete --change "<name>"
```

### 2. Write Implementation Report

Generate `implementation/implementation-report.md` aggregating all `task-reports/*.md`:
- Overall summary (total tasks, pass/fail, total files changed)
- Per-task summaries (ID, title, status, files, test results)
- Deviation log (if any deviations from plan were noted)

### 3. Write Deviation Report (if applicable)

If any task reports include deviations from the plan, write `implementation/deviation-observed.md` summarizing all deviations and their justifications.

### 4. Final Summary

Present to user:
- Total tasks completed
- All PR URLs (from `state.yaml` → `phase_pr_urls` for phase-iterative, or single PR URL for one-shot)
- Files changed across all tasks
- Test results aggregate
- Deviations (if any)

Output: "All implementation complete. PR(s) raised on upstream. Run `/opsx-archive` when ready."

### 5. Set State

Set state: `COMPLETE`. Write state.yaml.
