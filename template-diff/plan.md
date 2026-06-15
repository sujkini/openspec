# Template diff: `plan.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/plan.md` |
| Refined (eval workflow) | `evals/refined-templates/plan.md` |

## Status

**Changed** — +26 / -0 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/plan.md
+++ evals/refined-templates/plan.md
@@ -92,6 +92,28 @@
 - OLM/CSV/bundle constraints and upgrade edges

 - CI/e2e matrix impacts and MicroShift/OpenShift differences when spec mentions them

 

+### Addon operand planning supplements (when spec describes cert-manager-operator addon operands)

+- Separate phases for: API/CRD → unified manager wiring (`setup_manager.go`) → bindata → controller

+  reconcilers → status conditions → OLM bundle/CSV → e2e → documentation.

+- Map every new GA API field from validated_specs to ≥1 phase and ≥1 §6 verification matrix row.

+- Include OLM upgrade phase when a new owned CRD joins the bundle (N-1 → N operator upgrade testable).

+- Document singleton semantics (namespaced `default` vs cluster `cluster`) in §3.1 or phase goals.

+- Include **teardown phase** documenting limited CR-delete behavior (stop reconcile, manual cleanup

+  non-goals) per EP — do not plan full operand deletion unless spec requires it.

+- Include **operand version compatibility** row in §6: bindata version vs OSSM/Istio platform minimums.

+- Include **documentation phase** when integration docs ship: placeholder naming consistency AC.

+

+### Network policy planning supplements (when spec touches NetworkPolicy / defaultNetworkPolicy / networkPolicies[])

+- Use **separate phases** for: (1) OLM operator-namespace NP in bundle, (2) static/default managed NPs

+  (library-go path), (3) user-defined `networkPolicies[]` runtime reconciler — do not merge into one phase.

+- §6 verification matrix MUST include rows for:

+  - **Tamper-revert:** patch static-managed NP spec (e.g. egress port drift) → operator reverts within bounded time.

+  - **Delete-recreate:** delete user-defined NP → operator recreates promptly (watch/informer coverage).

+  - **Idempotent reconcile:** unchanged user-defined NP spec → no hot-loop patch/update.

+- Name controller type (library-go static vs runtime user-defined) in each verification row.

+- Include **per-component traffic matrix** rows in §6 when spec defines NP rules: API 6443, webhook 10250,

+  metrics 9402, DNS 53, operand-specific ports (e.g. istio-csr gRPC) — map each to a verification hook.

+

 ## Output hygiene

 - No preamble before the H1 title.

 - Use concrete but non-granular sequencing; phases are logical groupings, not day-by-day work.

@@ -106,6 +128,10 @@
 - [ ] All phases use the full phase template (Goal, Dependencies, Target files, Capabilities, Verification hooks)

 - [ ] Target files come only from repo_assessment.md or are marked UNVERIFIED + discovery step

 - [ ] §6 verification matrix has rows for Unit, Integration, E2E, Manual (or N/A with reason)

+- [ ] When spec touches NPs: §6 includes tamper-revert and delete-recreate rows per controller type

+- [ ] When spec describes addon operands: every new GA API field maps to a phase and verification row

+- [ ] When spec touches NPs: §6 includes per-component traffic matrix (6443, 10250, 9402, DNS, operand ports)

+- [ ] OLM N-1 → N upgrade and operand version compatibility have §6 rows when new CRD or bindata ships

 - [ ] §7 risks derived from repo_assessment §5 and §11.1 UNVERIFIED items

 - [ ] §8 complete — every open question has owner + default assumption; no truncated rows

 - [ ] No false "already exists" claims contradicted by repo_assessment branch verification

```
