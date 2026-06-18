# Template gaps — Round 3 Istio CSR (CM-463)

**Feature:** Istio CSR integration | **Round:** 3 | **Prior rounds:** Istio CSR (r1), Network Policy (r2)

## Summary

Round 1 artifact evals already cover all five bugs at workflow stage level. Round 3 primary gap:
**code-generation evals were never authored** (empty after rounds 1–2). Secondary: task payloads lacked
explicit `OAPE Command` tagging for `/opsx-apply` filtering.

## Template gap inventory

| Template | Gap | Resolution | Fixed |
|----------|-----|------------|-------|
| tasks.md | No OAPE command tagging in task payloads | patchable | Yes |
| validation.md | No bridge from retrospective patterns to code-generation evals | patchable | Yes |
| implementation.md | Code-gen guardrails present; no gap | eval-only | N/A |
| repo-assessment.md | Round 1 evals sufficient for istio | eval-only | N/A |
| constitution.md | Round 1 evals sufficient | eval-only | N/A |
| plan.md | Round 1 evals sufficient | eval-only | N/A |

## Artifact-stage evals (round 3)

Round 1 `eval-r001-*` cases already cover PAT-001–PAT-008 for this feature bundle. Round 3 adds
**eval-r003-*** cases focused on **code-generation bridge** and Service Mesh e2e coverage (PAT-015),
not duplicate round 1 assertions.

## Code generation evals

| oape_command | Cases | Evidence |
|--------------|-------|----------|
| api-implement | 3 | CM-735, CM-546, CM-973 |
| api-generate | 2 | CM-769 CEL, singleton CRD |
| api-generate-tests | 2 | IstioCSR API tests |
| e2e-generate | 2 | CM-546 Ready, CM-1043 smoke |
| manual | 3 | CM-521 bindata, CM-770 OLM, OCPBUGS-57841 docs |
| any | 1 | SSA not client.Create |

**Total:** 13 code-generation cases (exceeds minimum 2 per represented command).

## Deferred

- None
