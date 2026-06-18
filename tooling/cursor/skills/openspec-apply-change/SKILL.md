---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change via OAPE orchestration. Use when the user wants to start implementing, continue implementation, or work through tasks.
license: MIT
compatibility: Requires openspec CLI and OAPE commands in .cursor/commands/.
metadata:
  author: openspec
  version: "2.3"
---

Implement an OpenSpec change using OAPE command orchestration (see `/opsx:apply` and schema `oape_routing`).

**Reference:** `.cursor/commands/opsx-apply.md`

**Allowed OAPE commands (one per task):** `api-generate`, `api-generate-tests`, `api-implement`, `e2e-generate` (e2e tasks only). Do not use any other OAPE command.

**Input**: Optionally specify a change name. If omitted, infer from context or prompt.

**Steps**

1. **Select the change** — announce "Using change: <name>".

2. **Status and apply instructions**
   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```
   - `blocked` → suggest openspec-continue-change
   - `all_done` → suggest archive

3. **Prerequisites** — OAPE files: api-generate.md, api-generate-tests.md, api-implement.md, e2e-generate.md; gh/go/git/make; artifacts approved.

4. **Fork setup** — fork_repo_url from jira.yaml; clone; feature branch; cwd = fork root.

5. **Read contextFiles** from apply instructions.

6. **Parse tasks** from tasks.md §2 order; skip completed tasks.

7. **Task loop** (each pending task):
   - Compose `implementation/design-bundle.md` scoped to **current Task ID only**
   - Resolve **one** OAPE command:
     - IF e2e task → `e2e-generate`
     - ELIF API_Agent verification-only → `api-generate-tests`
     - ELIF API_Agent → `api-generate`
     - ELIF OperatorController_Agent → `api-implement`
     - ELIF manual agent → scoped edits (no OAPE)
   - Verify per task Acceptance criteria
   - **Gate:** "Approve task {id} ({title}) and proceed to the next task? (Approve / Reject with feedback)"
   - On approve: mark task `- [x]`, append phase log, advance
   - On reject: REVISION FEEDBACK; re-run current task only

8. **Post-loop** — report, checklist, adrs (if deviations), push, draft PR.

**Guardrails**
- Exactly **one** allowed OAPE command per task
- **Approval after every task** before advancing
- Never predict-regressions, review, or other OAPE commands
- OAPE commands in fork cwd only
- On reject: re-run current task only
