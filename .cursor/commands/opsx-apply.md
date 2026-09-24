---
name: /opsx-apply
id: opsx-apply
category: Workflow
description: Execute implementation tasks from tasks.md — state-machine driven (OPSX)
---

Execute tasks from `tasks.md` one at a time (or in auto-approve loop). This command is a thin router — all logic lives in skills.

**Input**: Optional change name after `/opsx-apply` (e.g. `/opsx-apply cm-830`).

## HARD RULES — NON-NEGOTIABLE

1. **Read `state.yaml` FIRST** — before any other action, every single invocation
2. **Read `codegen_mode`** — from `openspec/config.yaml` → `flags.codegen_mode` (default: `direct`)
3. **Read `auto_approve`** — from `openspec/config.yaml` → `flags.auto_approve` (default: `true`)
4. **When `auto_approve` is `false`: ONE task per invocation** — you MUST NOT execute more than one task in a single response. When you finish presenting a task for approval, your response is DONE.
5. **When `auto_approve` is `true`: ALL tasks in a loop** — auto-approve each task after eval/verification, write task report, and immediately proceed to the next task. Do NOT YIELD between tasks.
6. **YIELD = END YOUR RESPONSE** (only when `auto_approve` is `false`) — after the approval question, you MUST stop generating text.
7. **On user "approve"** (only when `auto_approve` is `false`) — write task report, mark complete, update state to IDLE, then STOP. Tell the user to run `/opsx-apply` again. Do NOT start the next task.
8. **Context windowing** — only load §4 payload for `current_task_id`, not all tasks
9. **Write state after every transition** — state must survive agent crashes
10. **No background sub-agents** — Do NOT launch background sub-agents, background shells, or Task-tool agents with `run_in_background=true`.
11. **Edit safety for existing source files** — never append to source files using `>>` / `tee -a`; use in-place edits only.
12. **No unsafe fallback rewrites** — if an existing file edit cannot be applied cleanly, STOP and request user guidance.

## Steps

### 1. Preflight

Read and follow `.cursor/skills/opsx-preflight/SKILL.md`.

### 2. Recovery Check

If preflight detects an in-flight state (`EXECUTING_TASK`, `RUNNING_TESTS`, `EVAL_GATE`):
Read and follow `.cursor/skills/opsx-recovery/SKILL.md`.

### 3. First Invocation Setup (no state.yaml)

On first run:
1. Select change (`openspec list --json` if name not given)
2. `openspec status --change "<name>" --json`
3. Verify prerequisites (artifacts approved, tools available)
4. Auto-fork: read `inputs/jira.yaml` → `target_repo`. Fork via GitHub MCP. Clone fork, create feature branch.
5. Create `implementation/` and `task-reports/` dirs
6. Parse tasks.md §2 order, set `total_tasks`
7. Initialize `state.yaml` from template
8. Recover/retry phase Jira ticket if needed (phase-iterative)
9. Fire telemetry: `on-apply-start`
10. Pick first pending task

### 4. Route by State

Read `.cursor/skills/apply-decisions.yaml` for the state-to-skill mapping.

| State | Action | Skill |
|-------|--------|-------|
| `IDLE` | Pick next pending task | `apply-execute-task/SKILL.md` |
| `EXECUTING_TASK` | Resume from crash | `opsx-recovery/SKILL.md` → `apply-execute-task/SKILL.md` |
| `RUNNING_TESTS` | Resume from crash | `opsx-recovery/SKILL.md` → `apply-execute-task/SKILL.md` |
| `EVAL_GATE` | Resume from crash | `opsx-recovery/SKILL.md` → `apply-ai-helpers/SKILL.md` |
| `AWAITING_APPROVAL` | Handle user approve/reject | (inline — see below) |
| `PHASE_COMPLETE` | Phase boundary | `apply-phase-boundary/SKILL.md` |
| `COMPLETE` | Done | Suggest `/opsx-archive` → STOP |

### 5. Handle Approval (AWAITING_APPROVAL)

**On approve:**
- Write `implementation/task-reports/<task-id>.md`
- Mark task `- [x]` in tasks.md
- Move `current_task_result` to `completed[]`, clear `rejections`
- Fire telemetry: `on-task-complete` (see `.cursor/skills/telemetry-hooks/SKILL.md`)
- Set state: `IDLE`
- **If `auto_approve: false`:** Output "Task {id} approved. Run `/opsx-apply` for next task." STOP.
- **If `auto_approve: true`:** Pick next pending task and loop back to step 4.

**On reject:**
- Append feedback to `rejections[]`
- Set state: `EXECUTING_TASK`
- Re-execute current task with revision feedback

### 6. Post-Loop / Phase Boundary

When all tasks for the current phase (phase-iterative) or all tasks (one-shot) are complete:

**One-shot:** Read and follow `.cursor/skills/apply-complete/SKILL.md` (includes PR prompt).
**Phase-iterative:** Read and follow `.cursor/skills/apply-phase-boundary/SKILL.md`.

PR creation: read and follow `.cursor/skills/apply-pr-creation/SKILL.md`.

## Telemetry

See `.cursor/skills/telemetry-hooks/SKILL.md` for all hook invocations.
