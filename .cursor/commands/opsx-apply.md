---
name: /opsx:apply
id: opsx-apply
category: Workflow
description: Implement tasks via OAPE command orchestration (task-by-task with approval after each task)
---

Implement an OpenSpec change using OAPE commands, driven by a composed design bundle
(tasks.md + upstream artifacts) scoped to **one task at a time**. **User approval
after every task** before advancing.

**Reference:** `oape-ai-e2e/AGENTS.md`, schema `oape_routing`, `.cursor/commands/oape-*.md`

**Input**: Optionally specify a change name (e.g., `/opsx:apply cm-830`). If omitted, infer from context or prompt.

## Steps

1. **Select the change**

   If a name is provided, use it. Otherwise infer, auto-select if only one active change,
   or run `openspec list --json` and ask the user.

   Announce: "Using change: <name>" and how to override.

2. **Check status and get apply instructions**

   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```

   Handle states:
   - `blocked` → suggest `/opsx:continue`
   - `all_done` → suggest archive
   - otherwise → proceed

3. **Verify prerequisites**

   - OAPE commands in `.cursor/commands/` (api-generate.md, api-implement.md, etc.)
   - `tasks.md`, `constitution.md`, `specs.md`, `plan.md` exist in change dir
   - `gh`, `go`, `git`, `make` available; `gh auth status` OK

4. **Fork setup** (before any OAPE command)

   - Read `openspec/changes/<name>/inputs/jira.yaml` for `fork_repo_url`
   - If missing, ask user once and persist
   - Clone or verify fork; create feature branch per schema `fork_repo.feature_branch`
   - Record `jira_key`; **all OAPE commands run with cwd = fork root**

5. **Read context artifacts**

   Read every path from apply instructions `contextFiles`:
   constitution.md, specs.md, plan.md, tasks.md, repo-assessment.md (if present)

6. **Parse tasks from tasks.md**

   - Order by §2 Linear Execution Order; respect §1 DAG
   - Skip tasks marked `- [x]`

7. **Task loop** (for each pending task in §2 order)

   ### Compose design bundle

   Write `openspec/changes/<name>/implementation/design-bundle.md` using
   `schemas/openspec-agile-workflow/templates/design-bundle.md`:
   - Include constitution, specs, plan, repo-assessment excerpts
   - Include §4 payload **ONLY for the current Task ID**
   - Derive API specification + Reconciliation workflow sections for OAPE
   - Add REVISION FEEDBACK when re-running after task rejection

   ### Run OAPE command (exactly one per task)

   Resolve command using this order:

   1. **IF e2e task** → `/oape:e2e-generate <fork-default-branch>`
      - Assigned Agent is `Testing_Agent`, OR
      - §4 Acceptance criteria references `make test-e2e`, OR
      - §4 Target file(s) under `test/`, OR
      - Title/Objective contains "e2e" or "end-to-end"
   2. **ELIF** `API_Agent` and verification-only → `/oape:api-generate-tests <api-path>`
   3. **ELIF** `API_Agent` → `/oape:api-generate --design-doc <bundle>` then `make update && make verify`
   4. **ELIF** `OperatorController_Agent` → `/oape:api-implement --design-doc <bundle>`
   5. **ELIF** manual agent → implement task payload directly (no OAPE command)

   Do **not** invoke predict-regressions, review, or any other OAPE command.

   Read `.cursor/commands/<command_file>` and execute its full workflow.

   ### Verify

   Run Makefile targets from **this task's** Acceptance criteria. Record pass/fail.

   ### Present task summary

   ```
   ## Task: <TASK_ID> — <title>
   Phase: <phase>

   ### OAPE Commands Executed
   | Command | Args | Outcome |

   ### Files Touched
   - path/to/file

   ### Test Results
   | Test | Result | Notes |

   ### Deviations (if any)
   ```

   ### User approval gate

   ASK: **"Approve task {task_id} ({task_title}) and proceed to the next task? (Approve / Reject with feedback)"**

   - **Reject** → add feedback to design-bundle REVISION FEEDBACK; re-run **this task only**; repeat from compose
   - **Approve** → mark task `- [x]` in tasks.md; append `implementation-phase-log.md`; advance to next task

8. **Post-loop** (all tasks approved)

   - Write `implementation-report.md`, `implementation-checklist.md`
   - Write `adrs.md` only if deviations logged
   - Commit, push feature branch, open draft PR on fork (`gh pr create --draft`)
   - Present final summary with draft PR URL

## Output During Implementation

```
## Implementing: <change-name> (OAPE orchestration)

Task 3/12: T1_3 — Implement controller reconciliation
→ /oape:api-implement --design-doc .../design-bundle.md
→ make test (PASSED)

Approve task T1_3 (Implement controller reconciliation) and proceed to the next task?
(Approve / Reject with feedback)
```

## Guardrails

- Invoke **exactly one** allowed OAPE command per task: api-generate, api-generate-tests, api-implement, or e2e-generate (e2e tasks only)
- **User approval gate after every task** — do not advance until approved
- Never use predict-regressions, review, or other OAPE commands during implementation
- Always compose fresh design-bundle.md per task (single Task ID scope)
- OAPE commands run in fork cwd only
- Do not advance on test failure without user decision
- On reject: re-run current task only
- Manual agents: minimal scoped edits per task payload; log deviations
- Read OAPE command files fully before executing — follow their prechecks
