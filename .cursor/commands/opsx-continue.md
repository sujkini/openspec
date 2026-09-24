---
name: /opsx-continue
id: opsx-continue
category: Workflow
description: Continue agile-workflow change - create next artifact, eval gate, refine, approve (OPSX)
---

Continue working on a change by creating the **next** artifact, then **eval → refine → approve**. When `auto_approve: true`, auto-loops through all remaining artifacts. This command is a thin router — all logic lives in skills.

**Input**: Optional change name after `/opsx-continue` (e.g. `/opsx-continue cm-830`).

## Steps

### 1. Preflight

Read and follow `.cursor/skills/opsx-preflight/SKILL.md`.

### 2. Pick Ready Artifact

Run `openspec status --change "<name>" --json`. Pick first artifact with `status: "ready"`.

If no artifacts are ready: all done. Output "All artifacts approved. Run `/opsx-apply` to begin implementation."

### 3. Pre-generation Checks

**If artifact is `tasks`:**
Read and follow `.cursor/skills/continue-phase-tasks/SKILL.md` for phase-specific setup.

**For all other artifacts:**
Read and follow `.cursor/skills/continue-artifact/SKILL.md`.

### 4. Generate, Eval, Approve

Read and follow `.cursor/skills/continue-artifact/SKILL.md` for:
- Artifact generation via `openspec instructions`
- Stage eval gate via `STAGE_EVAL_GATE_PROMPT.md`
- User approval (or auto-approve)
- On rejection: delegate to `.cursor/skills/continue-feedback-loop/SKILL.md`

### 5. Post-Approve Actions

After artifact approval:

**Jira Story creation** (when conditions match):
Read and follow `.cursor/skills/continue-jira-story/SKILL.md`.

### 6. Auto-Approve Loop

Read `config.yaml → flags.auto_approve`.

**When `auto_approve: true`:**
After steps 4-5 complete with `--status passed`, re-run `openspec status --change "<name>" --json`.
If another artifact has `status: "ready"`, loop back to step 2.
Continue until no more ready artifacts.

**When `auto_approve: false`:**
Process ONE artifact per invocation. Stop after approval + post-approval steps.

## Artifact Order

validation.json → specs.md → repo-assessment.md → [constitution.md check] → plan.md → tasks.md

## Guardrails

- When `auto_approve: false`: ONE artifact per invocation
- When `auto_approve: true`: loop through ALL ready artifacts
- Do not skip eval gate for artifacts with `gate: stage_evals`
- Do not refine **templates** during eval gate — refine the **change artifact** only
- `target_repo` required before repo-assessment
- **No background sub-agents**

## Telemetry

See `.cursor/skills/telemetry-hooks/SKILL.md` for all hook invocations.
Use `--batch` flags when processing multiple artifacts in auto-approve loop.
