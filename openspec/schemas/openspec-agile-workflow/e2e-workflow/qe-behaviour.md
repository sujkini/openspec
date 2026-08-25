# QE Behavioral Guidelines

Behavioral guidelines to reduce common LLM mistakes in QE workflows. Apply to all tasks: test writing, code review, test plan generation, and debugging.

**Tradeoff:** These guidelines bias toward precision and traceability over speed. For trivial tasks, use judgment.

## 1. Ask Before Assuming

**Don't invent requirements. Surface confusion early.**

- If the ADR or PR diff is ambiguous, ask — don't fabricate requirements.
- If multiple test approaches exist, present options — don't pick silently.
- If scope is unclear, state your interpretation and confirm before proceeding.
- If something contradicts the ADR, stop and flag the conflict.
- In PR Mode, if design intent is unclear from code alone, flag it as a gap.

## 2. Precision Over Volume

**One test per observable behavior. No padding.**

- Every test step must name a specific action AND a specific observable outcome.
- Never use vague verbs ("verify", "ensure", "check") without a named observable (e.g. condition `Ready=True`, HTTP 200, specific field value).
- Don't generate redundant tests that cover the same observable in multiple tiers.
- If you write 10 tests and 5 cover the same behavior, consolidate to 5.

Ask yourself: "Would a senior QE engineer say these are redundant?" If yes, deduplicate.

## 3. Surgical Scope

**Test only what the change covers. Nothing speculative.**

- Only test what the ADR's scope covers (or what the PR diff changes in PR Mode).
- Respect Non-Goals — don't generate tests for excluded behavior unless guarding against regression.
- Match existing test style (Ginkgo v2, Eventually/Consistently patterns, DeferCleanup).
- Never inline K8s resource specs (Pod, Deployment, etc.) in test files — use or create a builder helper in `test/e2e/utils/`. Duplicated specs drift silently (e.g. missing SecurityContext, wrong image).
- Before adding a DeferCleanup, check if the existing setup helper already registers cleanup for that resource. Don't revert a field on a resource that will be deleted entirely by the helper's cleanup — the revert is redundant.
- Never hardcode time durations (timeouts, polling intervals) in test files — use constants from `test/e2e/utils/constants.go` (e.g. `DefaultTimeout`, `ShortTimeout`, `DefaultInterval`, `ShortInterval`). If no suitable constant exists, add one to `constants.go` first.
- Don't refactor existing tests unless asked.

**Validation:** Every test case should trace directly to the ADR's stated goals/risks or the PR's changed behaviors.

## 3a. Operator Deployment Context — Template

> **This section is a template.** Operator teams fill in a copy at `qe-e2e/qe-behaviour.md` in their operator repository. The E2E workflow reads the operator's version at runtime.
> See `docs/qe-behaviour-example-ztwim.md` for a complete filled-in example.

Fill in the following for your operator:

- **Deployment method:** OLM / Helm / Manual / Other
- **Operator namespace:** `<operator-namespace>`
- **CSV / Deployment name pattern:** `<csv-or-deployment-name-pattern>`
- **Operand CR kinds and default names:**
  - `<CRKind1>` — default name: `<name>`
  - `<CRKind2>` — default name: `<name>`
- **Config patching method:** How to change operator configuration at runtime:
  - Subscription env patch / CSV patch / Deployment env / CR field / Other
  - Provide the `oc patch` or `kubectl` command template
- **Scaling method:** How to scale the operator (e.g., CSV patch for OLM, `kubectl scale` for direct deployments)
- **Things the agent must NEVER do:** (e.g., "Never use `oc scale deployment` — OLM will revert it")

## 3b. Operator Quality Gates — Template

> **This section is a template.** Operator teams fill in a copy at `qe-e2e/qe-behaviour.md` in their operator repository. Define the domain-specific quality gates that E2E tests must cover.
> See `docs/qe-behaviour-example-ztwim.md` for a complete filled-in example.

Fill in the relevant gate categories for your operator. Remove categories that don't apply.

### Operator Lifecycle
| Gate | Observable |
|------|------------|
| Installation | `<how to verify successful installation>` |
| Operator Health | `<deployment/pod health observable>` |
| Recovery | `<expected recovery behavior and timing>` |

### Operand Health
| Operand | Observable |
|---------|------------|
| `<Operand1>` | `<ready condition and workload status>` |
| `<Operand2>` | `<ready condition and workload status>` |

### Core Functionality (domain-specific)
| Gate | Observable |
|------|------------|
| `<core-gate-1>` | `<observable for domain-specific core behavior>` |
| `<core-gate-2>` | `<observable for domain-specific core behavior>` |

### Security
| Gate | Observable |
|------|------------|
| RBAC Minimal | `<ClusterRole permission boundaries>` |
| SCC/PSA | `<security context constraints or Pod Security Admission observable>` |
| Privilege Boundaries | `<UID/GID or non-root enforcement>` |

### Deployment Integration
| Gate | Observable |
|------|------------|
| `<OLM Upgradeable / Helm hooks / etc.>` | `<observable>` |

### Resilience
| Gate | Observable |
|------|------------|
| Pod Recovery | `<expected recovery after pod deletion>` |
| Config Reconciliation | `<operator restores modified resources?>` |

### Error Paths (optional)
| Scenario | Expected Behavior |
|----------|-------------------|
| `<dependency failure>` | `<expected operator behavior>` |
| `<invalid config>` | `<expected error handling>` |

### Performance (optional)
| Threshold | Value | Source |
|-----------|-------|--------|
| `<restart window>` | `<e.g., 60s>` | `<ADR/SLA>` |

**When writing tests:** Ensure critical gates (Operator Lifecycle, Operand Health, Core Functionality) are covered. For feature PRs, map new functionality to relevant gates.

## 4. Traceability Always

**Every test traces back to a source. No orphan tests.**

- In ADR Mode: every test traces to an ADR section or Jira acceptance criteria.
- In PR Mode: every test traces to a specific diff location (`file.go:L42`) or PR description.
- Never trace to commits or unrelated PRs.
- Every requirement traces to at least one test or has an explicit "NOT COVERED" with justification.
- Use stable IDs (REQ-001, PR-REQ-001, UT-001, E2E-001) that remain consistent across revisions.

## 5. Self-Verify Before Outputting

**Define success criteria. Loop until they pass.**

- Run quality gates before returning any test plan.
- If a gate fails, fix and re-verify — don't output a failing plan.
- Count coverage by tier and priority before finishing.
- For multi-step tasks, state a brief plan with verification checkpoints:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

## Stop Conditions (non-negotiable)

- No ADR and no PR provided → STOP, ask for ADR or PR link
- ADR has no "How" section → WARN user, generate with reduced Tier 1/2 coverage
- Jira conflicts with ADR → Document conflict, follow ADR, ask user to resolve
- More than 3 ambiguous requirements → STOP, list ambiguities, ask for clarification
- PR-only mode: more than 3 low-confidence requirements → WARN user, recommend ADR review

## Good vs Bad Examples

```
BAD step:  "Verify the operator works correctly"
GOOD step: "Assert status condition Ready=True on <OperandCR> within DefaultTimeout"

BAD step:  "Check security"
GOOD step: "Exec into operator pod; confirm process runs as non-root (UID != 0)"

BAD step:  "Ensure cleanup happens"
GOOD step: "Delete <OperandCR>; assert finalizer removes owned resources within DefaultTimeout"
```

---

**These guidelines are working if:** test plans have zero vague steps, every test traces to a requirement, no redundant tests exist across tiers, and clarifying questions come before generation rather than after mistakes.
