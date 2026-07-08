---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change via OAPE orchestration. Use when the user wants to start implementing, continue implementation, or work through tasks.
license: MIT
compatibility: Requires openspec CLI and OAPE commands in .cursor/commands/.
metadata:
  author: openspec
  version: "2.5"
---

Implement an OpenSpec change using OAPE command orchestration (see `/opsx:apply` and schema `oape_routing`, `code_generation_eval_gate`).

**Reference:** `.cursor/commands/opsx-apply.md`, `{schema_root}/stage-gate/CODE_GENERATION_EVAL_PROMPT.md`

**Allowed OAPE commands (one per task):** `api-generate`, `api-generate-tests`, `api-implement`, `e2e-generate` (e2e tasks only).

**Per-task mandatory sequence:**

```
OAPE (or manual — see `{schema_root}/templates/code-generation.md`) → verify → code-generation evals → refine code until pass (max 2 passes)
→ present scorecard → user approves CODE → write task report → next task
```

**Input**: Optionally specify a change name. If omitted, infer from context or prompt.

**Steps**

1. **Select the change** — announce "Using change: <name>".

2. **Status and apply instructions**
   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```

3. **Prerequisites** — OAPE command files; gh/go/git/make; artifacts approved; `implementation/task-reports/` dir.

4. **Fork setup** — fork_repo_url; clone; feature branch; cwd = fork root.

5. **Read contextFiles** from apply instructions.

6. **Parse tasks** from tasks.md §2 order; skip completed tasks.

7. **Task loop** (each pending task — **no user approval before eval gate completes**):
   - Compose `implementation/design-bundle.md` for **current Task ID only**
   - Run **one** OAPE command (or manual agent work per `{schema_root}/templates/code-generation.md`)
   - Verify task Acceptance criteria
   - **Code eval gate:** score fork code; refine until evals pass or 2 passes; write `eval-results/code-generation-<task-id>.yaml`
   - Present summary + code eval scorecard
   - **User approves code** for this task
   - **On approve:** write `implementation/task-reports/<task-id>.md`; mark `- [x]`; append phase log
   - **On reject:** REVISION FEEDBACK; re-run current task only

8. **Post-loop** — `implementation-report.md` aggregates all task reports; checklist; adrs; push; draft PR.

**Guardrails**
- Never ask user approval before code eval refinement loop completes (when cases exist)
- One OAPE command per task; approval after every task
- One task report per approved task
- OAPE in fork cwd only

## Dashboard Telemetry (optional — skip if backend not running)

Track the code-generation phase and per-task progress on the observability dashboard. All commands run from `dashboard/` directory (not fork cwd). Errors are non-fatal — ignore and continue if the dashboard backend is not running.

**Before the task loop** (after step 5 — reading context files):
```bash
cd dashboard && python -m src.telemetry.cli start-phase --change "<name>" --phase 5 --phase-name code_generation
```

**Before each task** (step 7, before composing design bundle):
```bash
cd dashboard && python -m src.telemetry.cli start-task --change "<name>" --task-id "<TASK_ID>" --title "<task_title>" --agent "<agent_id>"
```

**During task execution** — log notable events (OAPE command, verification, eval gate, self-correction):
```bash
cd dashboard && python -m src.telemetry.cli log --change "<name>" --agent "<agent_id>" --type tool_call --message "<what happened>"
cd dashboard && python -m src.telemetry.cli log --change "<name>" --agent "<agent_id>" --type harness_alert --message "<test/lint failure details>"
cd dashboard && python -m src.telemetry.cli log --change "<name>" --agent "<agent_id>" --type self_correction --message "Loop <N>/<max>: <refinement action>"
```

**After user approves a task** (step 7.7):
```bash
cd dashboard && python -m src.telemetry.cli end-task --change "<name>" --task-id "<TASK_ID>" --status passed --loops <refinement_passes>
```

**If a task is rejected and fails permanently**:
```bash
cd dashboard && python -m src.telemetry.cli end-task --change "<name>" --task-id "<TASK_ID>" --status failed --loops <refinement_passes>
```

**Post-loop** (step 8 — after all tasks approved):
```bash
cd dashboard && python -m src.telemetry.cli end-phase --change "<name>" --phase 5 --status passed --label "<summary>"
cd dashboard && python -m src.telemetry.cli end-run --change "<name>" --status completed
```
