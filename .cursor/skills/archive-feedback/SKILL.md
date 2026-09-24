# Archive Feedback Collection

Collect mandatory user feedback, time savings, and story points during `/opsx-archive`. This step is NON-SKIPPABLE.

## Hard Guardrail

You MUST complete this step before archiving. Do NOT skip, defer, or proceed to the archive move without collecting ALL FOUR responses, writing `user-feedback.md`, and recording the telemetry hook. If the user says "skip" or "just archive", respond: "Feedback collection is mandatory for compliance (MON-01). It takes 30 seconds. Please answer the four questions to proceed."

## Steps

### 1. Present Questions

Use **AskQuestion tool** with all four questions in a single prompt:

**Q1:** "How long would this change have taken without the agent? (estimated manual hours)"
- Options: "< 2 hours", "2-4 hours", "4-8 hours (1 day)", "8-16 hours (2 days)", "16-40 hours (1 week)", "> 40 hours (1+ weeks)"

**Q2:** "How satisfied are you with this run? (1 = poor, 5 = excellent)"
- Options: "1 - Poor", "2 - Below average", "3 - Average", "4 - Good", "5 - Excellent"

**Q3:** "Any comments on this run? (optional)"
- Options: "No comments" (user can type via "Other")

**Q4:** "How many story points were delivered for this ticket?" (MANDATORY)
- Options: "1", "2", "3", "5", "8", "13", "21+"
- Do not accept blank — re-prompt if skipped.

### 2. Write User Feedback

Write `openspec/changes/<name>/user-feedback.md`:
```markdown
# User Feedback — <change-name>

**Date:** YYYY-MM-DD
**Change:** <change-name>
**Jira:** <jira_key>

## Time Savings
- **Estimated manual effort:** <Q1>
- **Agent-assisted wall time:** <from telemetry if available>

## Satisfaction
- **Rating:** <Q2>

## Comments
<Q3 or "None">

## Productivity
- **Story points delivered:** <Q4>
```

### 3. Fire Telemetry

```bash
python -m openspec.telemetry.auto on-archive-feedback --change "<name>" \
  --story-points <Q4> --manual-effort "<Q1>" \
  --satisfaction <Q2> --comments "<Q3>"
```

This writes the `archive_feedback` event, sets `run.archived_at`, and regenerates `metrics-report.json` with `report_status.complete: true`.

**MUST run before the directory move** — it writes into the live change directory.

### 4. Verify Completeness

Check that `metrics-report.json` → `report_status.complete` is `true`. If not, flag to user before proceeding.
