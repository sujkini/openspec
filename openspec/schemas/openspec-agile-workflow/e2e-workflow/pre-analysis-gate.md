# Pre-Analysis Gate — ADR/PR Scoping & Approval

## Purpose

This rule produces a lean, scannable analysis document from an ADR or PR. The user reviews and approves (or modifies) this document **before** full test plan generation begins. This prevents wasted effort on misaligned test plans.

**Workflow:** User provides ADR/PR → **this rule generates pre-analysis** → user approves → auto-triggers `test-plan-e2e-generation` with the approved scope as input.

---

## 1. Input Handling

This rule supports the same input modes as `test-plan-e2e-generation`:

| Input provided | Mode |
| --- | --- |
| ADR only | ADR Mode |
| ADR + PR | ADR+PR Mode (PR enriches) |
| PR only | PR Mode |
| PR + Repo link | PR Mode (repo enriches) |
| Neither | STOP — ask for ADR or PR |

### How to fetch inputs

**PR:**
```bash
# PR metadata and diff
gh pr view <PR-NUMBER> --repo <org/repo> --json title,body,state,labels,files,additions,deletions,changedFiles
gh pr diff <PR-NUMBER> --repo <org/repo>

# Review comments — captures unresolved discussions, reviewer concerns, and context not in the diff
gh api repos/<org>/<repo>/pulls/<PR-NUMBER>/comments
gh api repos/<org>/<repo>/pulls/<PR-NUMBER>/reviews
```

**Review comments are mandatory input.** Unresolved reviewer concerns (e.g., "should this use runAsUser:65532?", "what about HostIPC?") often reveal scope gaps, contested design decisions, or incomplete implementation. Surface these in the analysis — either as regression risks, exclusions with justification, or items flagged for user clarification.

**ADR:** Accept Google Docs URL, GitHub file URL, local path, or pasted markdown. If fetch fails, ask the user to paste it.

### Stop condition

- No ADR and no PR → **STOP**, ask for input.
- Jira alone is not sufficient → **STOP**, ask for ADR or PR.

---

## 2. Change Type Classification

**Do this FIRST. It drives everything downstream.**

Classify the change into one of these categories based on the PR description/diff or ADR goals:

| Change Type | Testing Strategy |
| --- | --- |
| **Feature** | E2E-heavy — new positive-path + negative-path tests |
| **Bug Fix** | Regression-focused — reproduce the bug, verify the fix, guard against recurrence |
| **Refactor** | Regression-only — existing behavior must not change, minimal new tests |
| **Config** | Deployment/upgrade tests — verify config propagation and rollback |
| **Security** | Negative-heavy — privilege escalation, RBAC boundaries, admission control |
| **CRD Change** | API contract tests — validation, defaulting, backward compatibility |

If the change spans multiple types, pick the dominant one and note secondary concerns.

---

## 3. Impact Analysis (Files Touched)

### PR Mode
List all changed files from the diff. Categorize each:

| Category | File Patterns | Test Implication |
| --- | --- | --- |
| CRD Types | `api/**/*_types.go` | Field validation, status, E2E |
| Controllers | `internal/controller/**` | Reconcile logic, INT + E2E |
| Webhooks | `*_webhook.go` | Admission, INT + negative E2E |
| RBAC | `config/rbac/**` | Security (least privilege) |
| Samples | `config/samples/**` | Become E2E test inputs |
| Tests | `*_test.go` | Understand existing patterns |
| Config | `config/manager/**`, `Dockerfile` | Deployment/upgrade |
| Other | Everything else | Assess individually |

**Output:** Total file count, breakdown by category, new vs. modified vs. deleted.

### ADR Mode
Infer affected file areas from components described in the ADR (CRDs, controllers, operands, APIs). Map each to the category table above.

---

## 4. Existing Test Coverage Assessment

**Before proposing new tests, check what's already covered.**

1. Identify `*_test.go` files in affected directories.
2. For each affected component, determine:
   - Which existing tests cover it (by name/description)?
   - What behaviors are already validated?
   - Which existing tests may need **updating** due to this change?
3. Summarize as:
   - **Already covered:** Components/behaviors with existing test coverage (no new tests needed).
   - **Partially covered:** Existing tests exist but don't cover the new/changed behavior.
   - **Not covered:** No existing tests — net-new tests required.
   - **Needs update:** Existing tests that will break or become stale due to this change.

---

## 5. Blast Radius

### When `qe-behaviour.mdc` exists (MANDATORY)

**If a `qe-behaviour.mdc` file exists in the working directory, you MUST read it before completing this section.** Do not infer components or quality gates from the diff alone when this file is present.

Apply these rules in order:

1. **Component checklist (Section 3b):** Use the operand/component list from `qe-behaviour.mdc` Section 3b as the blast-radius checklist. Mark **every** listed component as affected or not affected — do not omit any.
2. **Quality gates table (Section 3b):** Use the domain-specific quality gate categories from `qe-behaviour.mdc` Section 3b (e.g., Operator Lifecycle, Operand Health, Identity & Attestation, Security, OLM Integration, Resilience) instead of the generic fallback table below.
3. **Deployment context (Section 3a):** Read `qe-behaviour.mdc` Section 3a and note OLM/deployment constraints (CSV/Subscription patching, namespace, operand CR naming) that affect E2E feasibility or step wording. Include these in the analysis under Dependencies or a brief "Deployment Context" note.
4. **Gate → test accountability:** Every quality gate marked **Affected** in this section MUST appear in **either** Section 7 (Proposed Tests) **or** Section 8 (Exclusions) with a code-level justification. Do not mark a gate affected and leave it unaccounted for in both sections.

If `qe-behaviour.mdc` is absent, use the generic component and quality gate frameworks below.

### Components Affected

Identify all components, operands, or services in the project that could be affected by this change. Derive the list from the repository structure (CRDs, controllers, operands, managed workloads, APIs).

**When `qe-behaviour.mdc` is present:** Start from its Section 3b component/operand list and check every entry.

Format as a checklist:
```
- [ ] <Component A>
- [ ] <Component B>
- [ ] <Component C>
- [ ] Operator Core (deployment, subscription, RBAC)
```

### Quality Gates Impacted

**When `qe-behaviour.mdc` exists:** Use its Section 3b quality gate categories and observables — not the generic table below.

**Otherwise**, use the generic quality gate framework:

| Gate Category | Affected? | Specific Gates |
| --- | --- | --- |
| Operator/App Lifecycle | Yes/No | Installation, Health, Recovery |
| Component Health | Yes/No | Which components reach ready state |
| Core Functionality | Yes/No | The primary domain behavior (e.g., identity issuance, data processing, routing) |
| Security | Yes/No | RBAC, admission, privilege boundaries, secrets |
| Deployment Integration | Yes/No | OLM, Helm, GitOps upgrade conditions |
| Resilience | Yes/No | Recovery, config reconciliation, self-healing |

### Risk Assessment

**Overall Risk Level:** Low / Medium / High / Critical

| Factor | Value | Weight |
| --- | --- | --- |
| Components touched | N | More components = higher risk |
| CRD schema changes | Yes/No | Schema changes = High risk |
| RBAC/Security boundaries | Yes/No | Security changes = High risk |
| Breaking change potential | Yes/No | Breaking = Critical risk |
| Upgrade path affected | Yes/No | Upgrade impact = High risk |

### Dependency Map
- **Upstream:** What feeds into the changed components
- **Downstream:** What depends on the changed components — what else could break

---

## 6. Regression Risk Map

**What existing behavior could break?**

| Area | Existing Test(s) | Risk | Why |
| --- | --- | --- | --- |
| e.g., Component readiness | `e2e_test.go:TestComponentReady` | Medium | Controller reconcile logic changed |

- List existing tests likely affected by this change.
- Flag behaviors that existing tests validate which might regress.
- Note API contracts that could break (field renames, type changes, removed defaults).

**Downstream tracing (mandatory):** For every quality gate marked as affected in the Blast Radius (Section 5), there MUST be a corresponding entry in this regression risk table — or an explicit "no risk because..." justification. Do not leave impacted quality gates unaccounted for.

**When `qe-behaviour.mdc` is present:** Use the **named gate categories** from its Section 3b in this check (e.g., if Blast Radius says "Identity & Attestation: Yes" but the regression table has no entry for SVID issuance or bundle distribution, the table is incomplete; if "OLM Integration: Yes" but no Upgradeable/CreateOnlyMode entry, the table is incomplete).

**Otherwise:** If the Blast Radius says "Core Functionality: Yes" but the regression table has no entry for the affected core behaviors, the table is incomplete.

**Specificity rule:** Every at-risk test must be referenced by its specific test name and file location (e.g., `e2e_test.go:"SPIRE Agent should be installed successfully"`). Search existing `*_test.go` files in affected directories for real test names — do not invent placeholder names. Never use "same test", "same E2E", "see above", or "multiple E2E contexts".

If no regression risk exists, state: **"No regression risk identified — change is additive."**

---

## 7. Proposed Test Cases (Preview)

**This is a lean preview — titles and one-liners only, not full test steps.**

Present in **priority order** (highest-value, highest-risk tests first):

| # | ID | Tier | Title | Description (one line) | Effort | Confidence | Maps To |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | E2E-001 | E2E | ... | ... | S/M/L | High/Med/Low | ADR §X or PR file:L42 |
| 2 | NEG-001 | NEG | ... | ... | S/M/L | High/Med/Low | ... |

**Priority ordering criteria:**
1. Critical risk + no existing coverage → top priority
2. High risk + partial coverage → high priority
3. New behavior (feature) → medium priority
4. Edge cases and exploratory → lower priority

**Gate coverage rule:** When `qe-behaviour.mdc` is present, every quality gate marked **Affected** in Section 5 must have at least one proposed test in this section **unless** it is explicitly excluded in Section 8 with a code-level reason (e.g., function defined but not called from controllers).

**Operand coverage rule:** When a change touches multiple operand controllers, propose at least one E2E test per affected operand using the **primary resource type modified in the PR diff** for that controller (e.g., DaemonSet reconciler change → DaemonSet conflict test, not a tangential SA test).

**Tier discipline:** UT and INT tests cover utility functions and recorder contracts — they do not substitute for E2E tests of operator behavior in a live cluster. Propose UT/INT only for pure functions; keep operand/controller behavior in E2E/NEG tiers.

### Estimated Distribution

| Tier | Proposed Count | Rationale |
| --- | --- | --- |
| E2E | 6–8 | Primary focus — user-facing scenarios |
| NEG | 3–4 | Operator resilience under destructive conditions |
| MQE | 2–3 | Acceptance + exploratory |
| INT | 2–3 | Only if reconciler/webhook interactions warrant it |
| UT | 2–3 | Only for new pure utility functions |
| NFT | 0–2 | Only if performance/recovery dimension exists |
| **Total** | **15–20** | |

### Effort Estimate

| Effort Tag | Meaning | Approximate Time |
| --- | --- | --- |
| **S** | Simple setup, single assertion | < 1 hour |
| **M** | Moderate setup, multiple assertions | 1–4 hours |
| **L** | Complex setup, multi-step scenario | 4+ hours |

**Total estimated effort range:** Sum of individual estimates.

---

## 8. What Will NOT Be Tested (Intentional Exclusions)

**Explicitly list what is out of scope and why.**

- Items from ADR Non-Goals section
- Components/files unchanged by the PR
- Behaviors already fully covered by existing tests (from Section 4)
- Areas explicitly excluded by the user

**Code-path verification (mandatory before excluding OR proposing update-path / Day-2 behavior):**

Before proposing tests for update-path, Day-2, or label-removal scenarios — or before excluding them — search the changed controller code to confirm the code path is actually invoked:

```
# Example: verify a utility is called from controllers (not just defined)
rg "FunctionName" pkg/controller/ --glob '*.go' --glob '!*_test.go'
```

- If a function is **defined but not called** from production controller code → exclude the behavior as speculative and cite the grep result.
- If PR description claims Day-2 behavior but the diff only adds create-path handling → exclude Day-2 and note the gap between description and implementation.

Format:
```
- <Excluded item> — Reason: <why it's excluded> (code evidence: <file or grep result>)
```

If the user does not see something they expected here, they should flag it before approval.

---

## 9. Analysis Confidence Score

Rate the overall confidence of this analysis:

| Level | Meaning |
| --- | --- |
| **High** | ADR available, clear scope, components well-understood |
| **Medium** | PR-only mode, most behaviors inferable from diff |
| **Low** | PR-only with complex/ambiguous changes, design intent unclear |

**Per-section confidence** (where relevant):
- Impact Analysis: High/Medium/Low
- Blast Radius: High/Medium/Low
- Proposed Tests: High/Medium/Low

**What would increase confidence:**
- e.g., "Provide the ADR for full design context"
- e.g., "Clarify whether field X is backward-compatible"

---

## 10. Output File

Save the generated analysis as:
```
e2e-analysis.md
```

This file is saved in the working directory. It is the **required input** for `test-plan-e2e-generation.mdc` — the test plan generator will not run without an approved `e2e-analysis.md`.

---

## 11. Output Template

Generate the analysis using this template. **Keep it scannable — target ~1 page.**

```markdown
# Pre-Analysis: <Feature/PR Title>

**Source:** <ADR link | PR link | both>
**Date:** <generation date>
**Mode:** ADR Mode | PR Mode | ADR+PR Mode
**Change Type:** Feature | Bug Fix | Refactor | Config | Security | CRD Change

---

## Impact
**Files:** N total (X new, Y modified, Z deleted)

| Category | Count | Key Files |
| --- | --- | --- |
| Controllers | N | `path/to/file.go` |
| CRD Types | N | `path/to/types.go` |
| ... | | |

## Existing Coverage
| Status | Component | Existing Test(s) |
| --- | --- | --- |
| Covered | <component> | `test_file.go:TestName` |
| Needs Update | <component> | `test_file.go:TestName` — reason |
| Not Covered | <component> | — (net-new test needed) |

## Blast Radius
**Components:** <checked list of affected components>
**Quality Gates Impacted:** <list from Section 3b>
**Risk Level:** Low / Medium / High / Critical
**Dependencies:** upstream → [changed component] → downstream

## Regression Risk
| Area | At-Risk Test | Risk Level | Why |
| --- | --- | --- | --- |
| ... | `TestName` | Med/High | ... |

_(or "No regression risk — change is additive.")_

## Proposed Tests (Priority Order)

| # | ID | Tier | Title | Effort | Confidence | Maps To |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | E2E-001 | E2E | ... | M | High | ADR §Goals / PR file:L42 |
| 2 | NEG-001 | NEG | ... | M | High | ... |
| ... | | | | | | |

**Distribution:** E2E: N | NEG: N | MQE: N | INT: N | UT: N | NFT: N | **Total: N**
**Estimated Effort:** X–Y hours

## Exclusions (Will NOT Test)
- <item> — Reason: <justification>
- <item> — Reason: <justification>

## Confidence
**Overall:** High / Medium / Low
**To increase confidence:** <what additional info would help>

---

## ACTION REQUIRED

Review this analysis and respond with one of:
- **Approved** — proceeds to full test plan generation automatically
- **Approved with changes** — specify modifications (add/remove/reorder tests, adjust scope)
- **Rejected** — specify what needs rework

_Once approved, this document becomes the scoping input for test plan generation. The test plan will respect the approved scope, priority ordering, and exclusions._
```

---

## 12. Approval Gate & Auto-Trigger Handoff

### Before approval
- Present the analysis document to the user.
- **STOP. Do not proceed to test plan generation.**
- Wait for the user to respond with Approved, Approved with changes, or Rejected.

### On "Approved with changes"
- Apply the user's modifications to the analysis document.
- Re-present the updated document for final confirmation.

### On "Approved"
1. Save the final approved analysis as `e2e-analysis.md` in the working directory.
2. **Automatically proceed to full test plan generation** using the rules in `test-plan-e2e-generation.mdc`.
3. The test plan generator reads `e2e-analysis.md` as its scoping input. It **MUST**:
   - Use the approved proposed test cases as the starting skeleton.
   - Respect the approved priority ordering.
   - Respect the approved exclusions — do not generate tests for excluded items.
   - Expand each proposed test case into full test steps (preconditions, steps, expected outcomes, cleanup).
   - Stay within the approved tier distribution (may adjust ±1 per tier if justified).
   - Reference the pre-analysis file in the test plan header.

### On "Rejected"
- Ask what needs rework.
- Re-run the analysis with the user's feedback incorporated.

---

## 13. Self-Verification Checklist

Before presenting the analysis to the user, verify:

```
[ ] Change type classified
[ ] All changed files listed and categorized (PR) or components mapped (ADR)
[ ] Existing test coverage assessed — not proposing tests for already-covered behaviors
[ ] qe-behaviour.mdc read (if present) — Section 3a deployment context noted, Section 3b used for component checklist and quality gates
[ ] Every component from qe-behaviour.mdc Section 3b marked affected or not (if qe-behaviour.mdc present)
[ ] Blast radius mapped to project quality gates (from qe-behaviour.mdc if present, or inferred from repo)
[ ] Every affected quality gate has a proposed test (Section 7) OR an exclusion with code evidence (Section 8)
[ ] Regression risk identified or explicitly marked as none
[ ] Regression risk table cites specific test names and file locations from existing *_test.go — no placeholders
[ ] Update-path / Day-2 behaviors verified against controller call sites before proposing or excluding
[ ] Proposed tests are priority-ordered with effort and confidence tags
[ ] Every proposed test maps to a specific ADR section or PR diff location
[ ] Multi-operand changes have at least one E2E test per affected operand (primary resource type from diff)
[ ] UT/INT proposed only for pure utilities — not as substitutes for operand E2E behavior
[ ] Exclusions section lists what will NOT be tested and why (with code evidence where applicable)
[ ] Overall confidence scored
[ ] Total proposed tests within 15–20 range
[ ] Review comments fetched (gh api pulls/NNN/comments + /reviews) and unresolved concerns surfaced
[ ] Document is scannable (~1 page, no walls of text)
```

If any check fails, fix it before presenting to the user.
