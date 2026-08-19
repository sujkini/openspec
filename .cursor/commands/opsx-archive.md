---
name: /opsx-archive
id: opsx-archive
category: Workflow
description: Archive a completed change in the experimental workflow
---

Archive a completed change in the experimental workflow.

**Input**: Optionally specify a change name after `/opsx:archive` (e.g., `/opsx:archive add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check artifact completion status**

   Run `openspec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `artifacts`: List of artifacts with their status (`done` or other)

   **If any artifacts are not `done`:**
   - Display warning listing incomplete artifacts
   - Prompt user for confirmation to continue
   - Proceed if user confirms

3. **Check task completion status**

   Read the tasks file (typically `tasks.md`) to check for incomplete tasks.

   Count tasks marked with `- [ ]` (incomplete) vs `- [x]` (complete).

   **If incomplete tasks found:**
   - Display warning showing count of incomplete tasks
   - Prompt user for confirmation to continue
   - Proceed if user confirms

   **If no tasks file exists:** Proceed without task-related warning.

4. **Assess delta spec sync state**

   Check for delta specs at `openspec/changes/<name>/specs/`. If none exist, proceed without sync prompt.

   **If delta specs exist:**
   - Compare each delta spec with its corresponding main spec at `openspec/specs/<capability>/spec.md`
   - Determine what changes would be applied (adds, modifications, removals, renames)
   - Show a combined summary before prompting

   **Prompt options:**
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, use Task tool (subagent_type: "general-purpose", prompt: "Use Skill tool to invoke openspec-sync-specs for change '<name>'. Delta spec analysis: <include the analyzed delta spec summary>"). Proceed to archive regardless of choice.

5. **User feedback and time savings — MANDATORY (NON-SKIPPABLE)**

   **HARD GUARDRAIL: You MUST complete this step before archiving. Do NOT skip, defer, or proceed to step 6 without collecting ALL THREE responses and writing `user-feedback.md`. If the user says "skip" or "just archive", respond: "Feedback collection is mandatory for compliance (MON-01). It takes 30 seconds. Please answer the three questions to proceed."**

   Present the following three questions to the user. Use the **AskQuestion tool** with all three questions in a single prompt:

   **Question 1:** "How long would this change have taken without the agent? (estimated manual hours)"
   - Options: "< 2 hours", "2–4 hours", "4–8 hours (1 day)", "8–16 hours (2 days)", "16–40 hours (1 week)", "> 40 hours (1+ weeks)"

   **Question 2:** "How satisfied are you with this run? (1 = poor, 5 = excellent)"
   - Options: "1 — Poor (major issues, significant rework)", "2 — Below average (multiple corrections needed)", "3 — Average (some corrections, acceptable output)", "4 — Good (minor corrections only)", "5 — Excellent (minimal or no corrections)"

   **Question 3:** "Any comments on this run? (optional — leave blank if none)"
   - Free text (the user can select "Other" and type a response, or select "No comments")
   - Options: "No comments"

   After collecting responses, write `openspec/changes/<name>/user-feedback.md`:

   ```markdown
   # User Feedback — <change-name>

   **Date:** YYYY-MM-DD
   **Change:** <change-name>
   **Jira:** <jira_key from inputs/jira.yaml, if available>

   ## Time Savings
   - **Estimated manual effort:** <user's answer to Q1>
   - **Agent-assisted wall time:** <total elapsed from telemetry if available, otherwise "not recorded">

   ## Satisfaction
   - **Rating:** <user's answer to Q2>

   ## Comments
   <user's answer to Q3, or "None">
   ```

   This file will be archived with the change directory in step 6.

6. **Perform the archive**

   Create the archive directory if it doesn't exist:
   ```bash
   mkdir -p openspec/changes/archive
   ```

   Generate target name using current date: `YYYY-MM-DD-<change-name>`

   **Check if target already exists:**
   - If yes: Fail with error, suggest renaming existing archive or using different date
   - If no: Move the change directory to archive

   ```bash
   mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
   ```

7. **Display summary**

   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Spec sync status (synced / sync skipped / no delta specs)
   - Note about any warnings (incomplete artifacts/tasks)

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs
**Feedback:** ✓ Captured (user-feedback.md)

All artifacts complete. All tasks complete.
```

**Output On Success (No Delta Specs)**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** No delta specs
**Feedback:** ✓ Captured (user-feedback.md)

All artifacts complete. All tasks complete.
```

**Output On Success With Warnings**

```
## Archive Complete (with warnings)

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
**Specs:** Sync skipped (user chose to skip)
**Feedback:** ✓ Captured (user-feedback.md)

**Warnings:**
- Archived with 2 incomplete artifacts
- Archived with 3 incomplete tasks
- Delta spec sync was skipped (user chose to skip)

Review the archive if this was not intentional.
```

**Output On Error (Archive Exists)**

```
## Archive Failed

**Change:** <change-name>
**Target:** openspec/changes/archive/YYYY-MM-DD-<name>/

Target archive directory already exists.

**Options:**
1. Rename the existing archive
2. Delete the existing archive if it's a duplicate
3. Wait until a different date to archive
```

**Guardrails**
- Always prompt for change selection if not provided
- Use artifact graph (openspec status --json) for completion checking
- Don't block archive on warnings - just inform and confirm
- Preserve .openspec.yaml when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, use the Skill tool to invoke `openspec-sync-specs` (agent-driven)
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
- **MANDATORY: Step 5 (user feedback) MUST be completed before step 6 (archive). Do NOT skip feedback collection. Do NOT archive without writing `user-feedback.md`. If the user attempts to skip, explain that feedback is required for compliance (MON-01) and re-prompt.**
