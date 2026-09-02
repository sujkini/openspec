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

5. **User feedback, time savings, and story points — MANDATORY (NON-SKIPPABLE)**

   **HARD GUARDRAIL: You MUST complete this step before archiving. Do NOT skip, defer, or proceed to step 6 without collecting ALL FOUR responses, writing `user-feedback.md`, and recording the telemetry hook below. If the user says "skip" or "just archive", respond: "Feedback collection is mandatory for compliance (MON-01). It takes 30 seconds. Please answer the four questions to proceed."**

   Present the following four questions to the user. Use the **AskQuestion tool** with all four questions in a single prompt:

   **Question 1:** "How long would this change have taken without the agent? (estimated manual hours)"
   - Options: "< 2 hours", "2–4 hours", "4–8 hours (1 day)", "8–16 hours (2 days)", "16–40 hours (1 week)", "> 40 hours (1+ weeks)"

   **Question 2:** "How satisfied are you with this run? (1 = poor, 5 = excellent)"
   - Options: "1 — Poor (major issues, significant rework)", "2 — Below average (multiple corrections needed)", "3 — Average (some corrections, acceptable output)", "4 — Good (minor corrections only)", "5 — Excellent (minimal or no corrections)"

   **Question 3:** "Any comments on this run? (optional — leave blank if none)"
   - Free text (the user can select "Other" and type a response, or select "No comments")
   - Options: "No comments"

   **Question 4:** "How many story points were delivered for this ticket?" — **MANDATORY, this is the field that determines whether metrics-report.json is considered complete.**
   - Options: "1", "2", "3", "5", "8", "13", "21+"
   - The user can select "Other" and type an exact number instead. Do not accept a blank answer — if the user tries to skip, re-prompt: "Story points delivered is mandatory. Without it, metrics-report.json will be marked incomplete."

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

   ## Productivity
   - **Story points delivered:** <user's answer to Q4>
   ```

   This file will be archived with the change directory in step 6.

   **Telemetry — record archive feedback (mandatory, before step 6):**

   Immediately after writing `user-feedback.md`, run:
   ```bash
   python -m openspec.telemetry.auto on-archive-feedback --change "<name>" \
     --story-points <Q4 answer> --manual-effort "<Q1 answer>" \
     --satisfaction <Q2 answer> --comments "<Q3 answer, or empty string if none>"
   ```
   This writes the `archive_feedback` telemetry event (which sets `run.archived_at`) and regenerates `metrics-report.json` with the `productivity_metrics` block and `report_status.complete: true`. It must run **before** step 6 moves the change directory, so the updated report is archived along with everything else. If this command fails or is skipped, `metrics-report.json` remains `report_status.complete: false` — flag this to the user before proceeding to step 6.

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
**Story Points Delivered:** <Q4 answer>
**Time Saved:** <productivity_metrics.time_saved_hours> hours (est.)
**Archived:** <run.archived_at_display, IST>
**Metrics:** ✓ Complete (metrics-report.json → report_status.complete: true)

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
**Story Points Delivered:** <Q4 answer>
**Time Saved:** <productivity_metrics.time_saved_hours> hours (est.)
**Archived:** <run.archived_at_display, IST>
**Metrics:** ✓ Complete (metrics-report.json → report_status.complete: true)

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
**Story Points Delivered:** <Q4 answer>
**Time Saved:** <productivity_metrics.time_saved_hours> hours (est.)
**Archived:** <run.archived_at_display, IST>
**Metrics:** ✓ Complete (metrics-report.json → report_status.complete: true)

**Warnings:**
- Archived with 2 incomplete artifacts
- Archived with 3 incomplete tasks
- Delta spec sync was skipped (user chose to skip)

Review the archive if this was not intentional.
```

**Output When Metrics Are Incomplete (telemetry hook failed before the move)**

```
## Archive Blocked — Metrics Incomplete

**Change:** <change-name>
**Feedback:** ✓ Captured (user-feedback.md)
**Metrics:** ⚠ Incomplete — metrics-report.json → report_status.complete: false
  Missing: productivity_metrics.story_points_delivered

The on-archive-feedback telemetry hook did not succeed. Do NOT proceed to step 6
(the directory move) until it succeeds — the hook writes into the live change
directory and cannot be run again once it has moved to openspec/changes/archive/.
Retry:
python -m openspec.telemetry.auto on-archive-feedback --change "<name>" --story-points <N> \
  --manual-effort "<Q1 answer>" --satisfaction <Q2 answer> --comments "<Q3 answer>"
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
- **MANDATORY: Step 5 (user feedback + story points) MUST be completed before step 6 (archive). Do NOT skip feedback collection. Do NOT archive without writing `user-feedback.md` AND successfully running the `on-archive-feedback` telemetry hook. If the user attempts to skip, explain that feedback and story points are required for compliance (MON-01) and re-prompt.**
- **Story points delivered (Question 4) is mandatory and gates `metrics-report.json` completeness — `report_status.complete` is `false` until it is recorded. Never invent a story points value; only use what the user provides.**
- **The `on-archive-feedback` telemetry hook MUST run before step 6 moves the change directory** — it writes into the live `openspec/changes/<name>/telemetry/` path, which only exists pre-move.
