# Template Gaps — Rounds 1–2 (full patchable backfill)

Patterns: PAT-001–PAT-014 | Bugs: CM-735, CM-546, CM-770, CM-521, OCPBUGS-57841, CM-758, CM-763, CM-764

## validation.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No addon-operator supplement rubric | High | patchable | **Yes** | Addon-operator supplements | round 1 evals |
| No network policy supplement rubric | High | patchable | **Yes** | Network policy supplements | eval-r002-* |

## repo-assessment.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| library-go vs runtime NP paths not required | High | patchable | **Yes** | Network policy dual-path §4.2 | eval-r002-repo-001 |
| Addon singleton default vs cluster not required | Med | patchable | **Yes** | Addon operand assessment block | eval-r001-repo-002 |
| GA API fields not required in assessment | Med | patchable | **Yes** | Addon operand assessment §4.1 | eval-r001-plan-001 |
| Per-component traffic matrix missing | High | patchable | **Yes** | §10.2 traffic matrix table | eval-r002-repo-002 |
| Operand version pin not required | Med | patchable | **Yes** | Addon assessment §4.3 cross-ref | eval-r001-repo-003 |

## constitution.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No addon unified-manager constraint | Med | patchable | **Yes** | Addon controllers | eval-r001-const-002 |
| Namespaced singleton default not stated | Med | patchable | **Yes** | Singleton semantics | eval-r001-const-001 |
| Limited teardown not in constraints | Med | patchable | **Yes** | CR delete / teardown | eval-r001-const-003 |
| Ready/Degraded lifecycle not required | High | patchable | **Yes** | Status conditions | eval-r001-tasks-001 |
| OLM upgrade constraint missing | High | patchable | **Yes** | OLM upgrade | eval-r001-plan-002 |
| Operand version matrix missing | Med | patchable | **Yes** | Operand version matrix | eval-r001-plan-003 |
| Doc placeholder consistency missing | Low | patchable | **Yes** | Documentation placeholders | eval-r001-tasks-003 |
| NP reconcile constraints | High | patchable | **Yes** | Network policy block | eval-r002-const-001 |
| Opt-in defaultNetworkPolicy not stated | Med | patchable | **Yes** | Opt-in security defaults | eval-r002-const-003 |

## plan.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No dual-controller / NP phase template | Med | patchable | **Yes** | NP planning supplements | eval-r002-plan-001 |
| No GA API field phase mapping for addons | Med | patchable | **Yes** | Addon operand supplements | eval-r001-plan-001 |
| No NP tamper/delete verification matrix | High | patchable | **Yes** | NP §6 rows + self-check | eval-r002-plan-003 |
| No per-component traffic matrix in §6 | High | patchable | **Yes** | Traffic matrix rows | eval-r002-plan-002 |
| No teardown phase guidance | Med | patchable | **Yes** | Teardown phase in addon supplements | eval-r001-impl-003 |
| No OLM upgrade / version skew §6 rows | High | patchable | **Yes** | OLM + version compatibility + self-check | eval-r001-plan-002/003 |
| No documentation phase | Low | patchable | **Yes** | Documentation phase in addon supplements | eval-r001-tasks-003 |

## tasks.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No NP-specific verification pairing | High | patchable | **Yes** | Operand reconcile features | eval-r002-tasks-* |
| No status-condition pairing for addons | High | patchable | **Yes** | Status condition pairing | eval-r001-tasks-001 |
| No OLM upgrade verification pairing | High | patchable | **Yes** | OLM and release verification | eval-r001-plan-002 |
| No bindata version compatibility tasks | Med | patchable | **Yes** | OLM and release verification | eval-r001-plan-003 |
| No documentation placeholder AC | Low | patchable | **Yes** | Documentation tasks | eval-r001-tasks-003 |
| No controller Watches tasks | High | patchable | **Yes** | Controller watches section | eval-r002-tasks-002 |

## implementation.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| No compare-before-update guardrail | High | patchable | **Yes** | Reconciler guardrails | eval-r002-impl-002 |
| No unified manager wiring note | Med | patchable | **Yes** | Unified manager wiring | eval-r001-impl-001 |
| No Ready condition implementation note | High | patchable | **Yes** | Status conditions | eval-r001-impl-002 |
| No limited teardown guardrail | Med | patchable | **Yes** | Limited teardown on CR delete | eval-r001-impl-003 |
| No static NP drift revert note | High | patchable | **Yes** | Static managed resources | eval-r002-impl-001 |
| No NetworkPolicy Watches note | High | patchable | **Yes** | User-defined Watches | eval-r002-impl-003 |

## tasks-modes/single.md

| Gap | Severity | Resolution | Fixed | Template patch | Eval |
|-----|----------|------------|-------|----------------|------|
| Drift/delete pairing not in checklist | Med | patchable | **Yes** | Completeness + self-check | eval-r002-tasks-* |
| OLM/docs/watches not in checklist | Med | patchable | **Yes** | Completeness + self-check | eval-r001/r002 tasks |
