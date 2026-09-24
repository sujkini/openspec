---
name: /opsx-archive
id: opsx-archive
category: Workflow
description: Archive a completed change in the experimental workflow
---

Archive a completed change. This command is a thin router — feedback and telemetry logic lives in skills.

**Input**: Optional change name (e.g. `/opsx-archive add-auth`). If omitted, prompt for selection.

## Steps

### 1. Select Change

If no change name provided: run `openspec list --json`, use **AskQuestion** to let user select. Show only active (non-archived) changes. Do NOT auto-select.

### 2. Check Completions

Run `openspec status --change "<name>" --json` to check artifact completion.
- If incomplete artifacts: warn, prompt for confirmation.
- Read tasks.md for incomplete tasks (`- [ ]`). If found: warn, confirm.

### 3. Delta Spec Sync

Check for delta specs at `openspec/changes/<name>/specs/`.
- If exist: compare with main specs, show summary, prompt: "Sync now (recommended)" / "Archive without syncing"
- If synced or none: proceed.

### 4. User Feedback (MANDATORY)

Read and follow `.cursor/skills/archive-feedback/SKILL.md`.

This step is NON-SKIPPABLE. All four questions must be answered, `user-feedback.md` written, and `on-archive-feedback` telemetry fired before proceeding.

### 5. QE Feedback (CONDITIONAL)

Read and follow `.cursor/skills/archive-qe-feedback/SKILL.md`.

Only runs if `openspec/changes/<name>/telemetry/e2e-events.jsonl` exists. Also NON-SKIPPABLE when triggered.

### 6. Perform Archive

```bash
mkdir -p openspec/changes/archive
mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
```

Check target doesn't already exist. Fail with guidance if it does.

### 7. Display Summary

Show archive completion: change name, schema, archive location, spec sync status, feedback status, story points, metrics completeness.

### 8. External Feedback Form (MANDATORY display)

Always show the external agent feedback form link after archive:
```
## One more step — Agent feedback form

**[Submit Agent Feedback Here](https://docs.google.com/spreadsheets/d/1lBhSpvjtceexzHGc-dF37F6ho2y4msUnXm5hg52gMus/edit?usp=sharing)**
```

## Guardrails

- Step 4 (feedback) MUST complete before step 6 (archive move)
- Step 5 (QE feedback) MUST complete before step 6 when E2E ran
- Telemetry hooks MUST run before the directory move (they write into the live path)
- Story points (Q4) is mandatory and gates `report_status.complete`
- Step 8 (external form) MUST always display after successful archive
