# Quality Checklist

**Feature**: [FEATURE_NAME]
**Date**: [DATE]

## Spec Quality

- [ ] All user stories have acceptance criteria (Given/When/Then)
- [ ] Every requirement is testable and unambiguous
- [ ] No implementation details in spec (languages, frameworks, APIs)
- [ ] Success criteria are measurable and technology-agnostic
- [ ] Maximum 3 [NEEDS CLARIFICATION] markers
- [ ] Edge cases documented

## Plan Quality

- [ ] Every decision traces to spec requirement or constitution principle
- [ ] Every risk traces to repo assessment finding or spec gap
- [ ] Implementation phases have clear goals and verification hooks
- [ ] No orphan decisions (all justified)
- [ ] Critical path identified

## Task Quality

- [ ] Every FR-xx and SC-xx mapped to at least one task
- [ ] Every plan phase mapped to tasks
- [ ] Tasks are at file/package granularity
- [ ] No task exceeds complexity 8 (split if needed)
- [ ] Dependencies are explicit and acyclic
- [ ] Per-task payloads include acceptance criteria

## Implementation Readiness

- [ ] Repo assessment target files verified
- [ ] Reusable assets identified (anti-duplication)
- [ ] Architectural guardrails documented
- [ ] Risks have mitigations
- [ ] Open questions have default assumptions
