# Template diff: `tasks.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/tasks.md` |
| Refined (eval workflow) | `evals/refined-templates/tasks.md` |

## Status

**Changed** — +53 / -0 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/tasks.md
+++ evals/refined-templates/tasks.md
@@ -67,3 +67,56 @@
 

 Read **AgentRoutingMode** and **ConstitutionVersion** from constitution.md header — do NOT hardcode

 PROVISIONAL when constitution says PROVIDED.

+

+## Output mode

+

+Default: single-pass per `tasks-modes/single.md` (§0–§5). Use other modes from `tasks-modes/` only when

+the user message specifies them.

+

+## Verification pairing (mandatory)

+

+For every substantive implementation task (controller, deployment, RBAC, bindata, OLM, webhook):

+

+1. Add a **paired verification task** (unit, integration, or e2e per constitution) that depends on the

+   implementation task.

+2. Verification task payloads MUST name Makefile targets from repo_assessment (e.g. `make test`, not

+   invented targets).

+3. Trace acceptance criteria to validated_specs.md FR/AC IDs.

+

+### Operand reconcile features (addon controllers, NetworkPolicy, deployments)

+

+When tasks touch reconciliation of operator-managed operands:

+

+- Pair **status condition** tasks with deployment/controller tasks (`Ready` / `Degraded`, `updateStatus`).

+- Pair **operand drift** e2e: tamper managed resource spec → assert operator reverts (static/library-go NPs).

+- Pair **delete-recreate** e2e: delete user-defined managed resource → assert prompt recreate.

+- Pair **idempotent reconcile** unit/integration: unchanged spec → no patch (compare-before-update).

+

+Document paired Task IDs in §0 input coverage checklist.

+

+### OLM and release verification (when plan includes bundle/CRD changes)

+

+- Pair CSV/bundle changes with **OLM upgrade verification** task: install N-1 operator → upgrade to N →

+  assert owned CRD/subscription healthy (driver: CM-770 pattern).

+- Pair bindata/operand version bumps with **platform compatibility** verification against OSSM/Istio

+  minimums from EP (driver: CM-521 pattern).

+

+### Documentation tasks (when plan includes docs phase)

+

+- Route to `Docs_Agent` (or agents.md equivalent) with acceptance criteria for **placeholder naming

+  consistency** across examples (e.g. single canonical `<istio_project_name>` — driver: OCPBUGS-57841).

+

+### Controller watches (user-defined managed resources)

+

+- When tasks add runtime reconcilers for user-defined resources (e.g. `networkPolicies[]`), include

+  explicit task for `Watches()` on managed GVK with delete/recreate predicates (driver: CM-764 pattern).

+

+## Quality self-check

+

+- [ ] Every substantive implementation task has a paired verification task

+- [ ] Reconcile/drift scenarios from plan §6 have explicit e2e or integration tasks

+- [ ] §3 manifest row count equals §4 payload subsection count

+- [ ] Assigned Agent values match agents.md (PROVIDED) or provisional IDs exactly

+- [ ] OLM upgrade and bindata version tasks paired with verification when plan requires them

+- [ ] Documentation tasks include placeholder consistency AC when integration docs are in scope

+- [ ] User-defined resource controllers have explicit watch/informer tasks when plan §6 requires delete-recreate

```
