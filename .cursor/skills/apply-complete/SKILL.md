# Apply Complete

Finalize the implementation after all tasks (one-shot) or all phases (phase-iterative) are done.

## Steps

### 1. Telemetry

```bash
python -m openspec.telemetry.auto on-apply-complete --change "<name>"
```

### 2. Final Summary

Present to user:
- Total tasks completed
- All PR URLs (from `state.yaml` → `phase_pr_urls` for phase-iterative, or single PR URL for one-shot)
- Files changed across all tasks
- Test results aggregate

Output: "All implementation complete. PR(s) raised on upstream. Run `/opsx-archive` when ready."

### 3. Set State

Set state: `COMPLETE`. Write state.yaml.
