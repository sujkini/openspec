# Phase Boundary

Handle the transition between phases in `phase-iterative` mode. Called when all tasks for the current phase are complete.

## Steps

### 1. Phase Summary

Set state: `PHASE_COMPLETE`. Write state.yaml.

Present phase summary:
- Tasks completed (count, IDs)
- Files changed across all phase tasks
- Test results (pass/fail counts)

Fire telemetry:
```bash
python -m openspec.telemetry.auto on-phase-complete --change "<name>" --phase <N> --pr-raised <true|false>
```

### 2. Phase Approval Gate

Read `config.yaml → flags.auto_approve`.

**If `auto_approve: true`:** Auto-approve phase. Skip prompt. Proceed to step 3.

**If `auto_approve: false`:**
- Persist `phase_feedback_rounds: 0` to state.yaml.
- ASK: "Phase {N} development complete. All tasks pass verification. Approve the phase implementation? (Approve / Reject with feedback)"
  - **On approve:** proceed to step 3.
  - **On reject:** user provides feedback. Increment `phase_feedback_rounds`. Apply fixes, re-run verification. Re-prompt. Max 3 rounds.

### 3. PR Prompt (ALWAYS prompted)

ASK: "Phase {N} approved. Would you like to raise a PR to the upstream repo? (Yes / No)"

This prompt is NEVER auto-approved. `auto_approve` does NOT apply to PR creation.

**If yes:** delegate to `.cursor/skills/apply-pr-creation/SKILL.md` for phase PR.

Record URL in `state.yaml` → `phase_pr_urls`.

### 4. Advance Phase

Check if `current_plan_phase >= total_plan_phases`:

**All phases done:**
- Delegate to `.cursor/skills/apply-complete/SKILL.md`

**Phases remain:**
- Update `state.yaml`: `current_plan_phase = N+1`, state = `IDLE`, reset `phase_feedback_rounds: 0`
- **If `auto_approve: false`:** Output "Phase {N} complete. Run `/opsx-continue` to generate Phase {N+1} tasks." YIELD.
- **If `auto_approve: true`:** Output "Phase {N} complete. Auto-triggering `/opsx-continue` for Phase {N+1}." Automatically invoke `/opsx-continue` to generate next-phase tasks. Then loop back to execute tasks.
