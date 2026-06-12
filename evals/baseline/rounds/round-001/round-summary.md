# Round 1 Summary — Istio CSR integration

**Epic:** CM-463 | **GA Strat:** OCPSTRAT-1974 | **Bugs:** 5

## Epic Bug Analysis

- **Patterns identified:** 8 (PAT-001 through PAT-008)
- **Issues classified:** 5 (1 design, 1 story_formation, 2 coding, 1 ops_docs)

## Eval Generation

| Stage | Evals added |
|-------|-------------|
| repo-assessment | 3 |
| constitution | 3 |
| plan | 3 |
| tasks | 3 |
| implementation | 3 |
| **Total** | **15** |

## Templates changed

- `validation.md` — addon-operator supplement rubric

## Top lessons for round 2

1. Unified manager cache is non-negotiable for addons (CM-735)
2. OLM upgrade must be planned when adding CRDs (CM-770)
3. Ready condition must be tasked and tested (CM-546)
4. Operand version matrix must be in plan verification (CM-521)

## Next step

Replace `evals/inputs/` with next feature bundle and run `/eval-loop` — baseline evals feed round 2.
