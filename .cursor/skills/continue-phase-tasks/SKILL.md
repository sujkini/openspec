# Phase Tasks Setup

Handle `task_execution_mode` check and phase-specific task generation logic. Called by `continue-artifact` skill when the next ready artifact is `tasks`.

## Steps

### 1. Read Execution Mode

Read `config.yaml → flags.task_execution_mode` (default: `phase-iterative`).

### 2. Phase-Iterative Mode

- Read `implementation/state.yaml` (or initialize if missing) to get `current_plan_phase` (default: 1) and `total_plan_phases`.
- If `current_plan_phase > total_plan_phases`: all phases done — skip task generation; proceed to archive. STOP.
- Read `plan.md` and extract Phase N details (goal, target files, dependencies, verification hooks).
- Set `phase_scope: N` in generation context metadata.
- If Phase N > 1: existing tasks.md contains prior phases marked `[x]` — new tasks will be appended.

### 3. One-Shot Mode

- Do NOT set `phase_scope` metadata (generate all phases at once).
- tasks.md is generated once covering ALL plan phases.
- No state.yaml phase tracking needed at this stage.

### 4. Task Sizing Prompt

Read `config.yaml → flags.task_sizing`. If `prompt_user` is true:

**Phase-iterative:**
```
Phase {N} of plan.md: {phase_goal}.
How many tasks for this phase?
Enter a range: min max (e.g. "2 3")
Press Enter to use defaults ({default_min}–{default_max}).
```

**One-shot:**
```
plan.md has {N} implementation phases.
How many total tasks should this change produce?
Enter a range: min max (e.g. "2 5")
Press Enter to use defaults ({default_min}–{default_max}).
```

Parse response. Empty → defaults from config (min: 2, max: 3).
Inject into generation context as `task_sizing: { min: X, max: Y }`.
If `prompt_user` is false: inject defaults silently (no prompt).

**Do NOT re-prompt during eval gate, feedback loop, or regeneration.**
