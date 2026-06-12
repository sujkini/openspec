# Validation Template Refinements — Round 2

## Rationale

Network Policy bugs (CM-758, CM-763, CM-764) exposed gaps not covered by round 1 addon-operator supplements.

## Change applied

**File:** `schemas/openspec-agile-workflow/templates/validation.md`

**Section added:** `### Network policy supplements` under Completeness rubric

**New checks:**
- Dual controller paths (static library-go vs user-defined)
- Opt-in `defaultNetworkPolicy` backward compatibility
- Per-component traffic matrix
- Drift reconciliation test for static NPs
- Idempotent reconcile for user-defined NPs
- Delete/recreate watch requirements
- Operator OLM vs operand CR-driven NPs

## Round 1 interaction

Round 1 addon supplements remain; round 2 adds NP-specific layer when spec touches NetworkPolicy fields.
