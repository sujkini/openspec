# Template Gaps — Rounds 1–2 (backfill applied)

## validation.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No addon-operator supplement rubric | High | patchable | **Yes** | Completeness → Addon-operator supplements | round 1 evals |
| No network policy supplement rubric | High | patchable | **Yes** | Completeness → Network policy supplements | eval-r002-* |

## repo-assessment.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| library-go vs runtime NP paths not required | High | patchable | **Yes** | Network policy dual-path under §4.2 | eval-r002-repo-001 |

## constitution.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No addon unified-manager constraint | Med | patchable | **Yes** | cert-manager-operator supplements → Addon controllers | eval-r001-* |
| No NP reconcile constraints | High | patchable | **Yes** | cert-manager-operator supplements → Network policy | eval-r002-* |

## plan.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No dual-controller / NP phase template | Med | patchable | **Yes** | Network policy planning supplements | eval-r002-plan-001 |
| No GA API field phase mapping for addons | Med | patchable | **Yes** | Addon operand planning supplements | eval-r001-plan-001 |
| No NP tamper/delete verification matrix | High | patchable | **Yes** | NP supplements + §6 rows + quality self-check | eval-r002-plan-003 |

## tasks.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No NP-specific verification pairing | High | patchable | **Yes** | Verification pairing + Operand reconcile features | eval-r002-tasks-001/002/003 |
| No status-condition pairing for addons | High | patchable | **Yes** | Operand reconcile features (Ready/updateStatus) | eval-r001-tasks-001 |

## implementation.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No compare-before-update guardrail | High | patchable | **Yes** | Reconciler guardrails section | eval-r002-impl-002 |
| No unified manager wiring note | Med | patchable | **Yes** | Reconciler guardrails (static vs runtime) | eval-r001-impl-001 |

## tasks-modes/single.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| Drift/delete pairing not in mode checklist | Med | patchable | **Yes** | Completeness rules + quality self-check | eval-r002-tasks-* |

## Round 1 eval strengthened (eval-only update)

- `eval-r001-tasks-001` — added `should_cover_operand_drift_tests` for NP scenarios (CM-758, CM-764)
