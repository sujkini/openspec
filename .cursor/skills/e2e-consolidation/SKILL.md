# E2E Journey Consolidation (Stage 2b)

Consolidate the test plan's journeys to the configured maximum. Applied when the test plan exceeds `config.yaml → qe.max_test_cases`.

## Inputs

- Approved `test-plan.md` (from Stage 2)
- `config.yaml → qe.max_test_cases` (consolidation target)

## Process

Apply Section 12 of `test-plan-generation.md` (Journey Consolidation).

1. Count journeys in `test-plan.md`
2. If count <= `max_test_cases`: skip consolidation, write `revised-test-plan.md` as copy
3. If count > `max_test_cases`:
   - Merge journeys that test the same CR/component into combined journeys
   - Prioritize by risk tier (Tier 1 stays, Tier 3 gets merged/dropped first)
   - Preserve traceability links
   - Write `openspec/changes/<name>/e2e/revised-test-plan.md`

## Approval Gate

Present consolidation summary (original count → revised count, merged journeys, dropped coverage).
Wait for user approval.
- On reject: adjust consolidation with feedback
- On approve: proceed to Stage 3 (code generation)
