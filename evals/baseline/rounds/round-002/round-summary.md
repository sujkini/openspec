# Round 2 Summary — Network Policy hardening

**Epics:** CM-802 (operator), CM-525 (operand) | **Bugs:** CM-758, CM-763, CM-764

## Feedback loop from round 1

- Loaded 15 round-1 evals + refined `validation.md`
- Round-1 evals **insufficient** for NP-specific patterns
- Strengthened `eval-r001-tasks-001` with operand drift test requirements

## Epic Bug Analysis

- **New patterns:** PAT-009 through PAT-014 (6 patterns)
- **Issues:** 3 (all coding)
- **Recurrence:** 0 recurring from round 1

## Eval Generation

| Stage | Added | Updated |
|-------|-------|---------|
| repo-assessment | 3 | 0 |
| constitution | 3 | 0 |
| plan | 3 | 0 |
| tasks | 3 | 1 (r001-tasks-001) |
| implementation | 3 | 0 |
| **Total** | **15** | **1** |

## Templates changed

- `validation.md` — network policy supplements (layered on round 1 addon supplements)

## Top lessons

1. cert-manager **core** features use library-go — different eval path than addons (CM-758)
2. Compare-before-update mandatory for hot-loop prevention (CM-763)
3. User-defined resources need explicit NP watches (CM-764)

## Cumulative baseline

- **30 eval cases** across 2 rounds
- **14 patterns** (PAT-001–PAT-014)
