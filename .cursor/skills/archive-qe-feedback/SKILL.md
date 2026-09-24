# Archive QE Feedback Collection

Collect QE/E2E feedback during `/opsx-archive`. CONDITIONAL — only runs if this change had an E2E run.

## Trigger Check

```bash
test -f openspec/changes/<name>/telemetry/e2e-events.jsonl && echo "e2e_ran" || echo "no_e2e"
```

- **If `no_e2e`:** Skip entirely. Do not ask QE questions. Do not create `qe-metrics.json`.
- **If `e2e_ran`:** Proceed — this is MANDATORY and NON-SKIPPABLE.

## Steps

### 1. Present QE Questions

Use **AskQuestion tool** with all four questions:

**Q1:** "How long would the E2E/QE work have taken without the agent?"
- Options: "< 2 hours", "2-4 hours", "4-8 hours (1 day)", "8-16 hours (2 days)", "16-40 hours (1 week)", "> 40 hours (1+ weeks)"

**Q2:** "How satisfied are you with the E2E/QE workflow? (1 = poor, 5 = excellent)"
- Options: "1 - Poor", "2 - Below average", "3 - Average", "4 - Good", "5 - Excellent"

**Q3:** "Any feedback on the E2E/QE workflow? (optional)"
- Options: "No comments" (user can type via "Other")

**Q4:** "How many story points does the QE/test coverage represent?" (MANDATORY)
- Options: "1", "2", "3", "5", "8", "13", "21+"

### 2. Append to User Feedback

Append QE section to existing `openspec/changes/<name>/user-feedback.md`:
```markdown

## QE / E2E Feedback
- **Estimated manual effort:** <Q1>
- **Satisfaction:** <Q2>
- **Story points (QE/test coverage):** <Q4>
- **Comments:** <Q3 or "None">
```

### 3. Fire Telemetry

```bash
python -m openspec.telemetry.auto on-qe-archive-feedback --change "<name>" \
  --story-points <Q4> --manual-effort "<Q1>" \
  --satisfaction <Q2> --comments "<Q3>"
```

This writes the `qe_archive_feedback` event and regenerates `qe-metrics.json` with `qe_report_status.complete: true`.

**MUST run before the directory move.**

### 4. Verify Completeness

Check `qe-metrics.json` → `qe_report_status.complete` is `true`. If not, flag to user.
