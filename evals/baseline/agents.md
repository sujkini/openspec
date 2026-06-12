# Baseline agents.md — refined routing notes from eval loops

## Round 1 — Istio CSR (CM-463)

### Addon controller architecture (from CM-735 / PAT-003)

- All addon controllers **must** register in `pkg/operator/setup_manager.go` on the **single** unified `ctrl.Manager`.
- **Do not** create separate `ctrl.Manager` instances or isolated caches per addon.
- IstioCSR exemplar: `pkg/controller/istiocsr/` — follow controller-runtime + SSA pattern.

### Singleton CR conventions

- IstioCSR: **namespaced** singleton with `metadata.name == 'default'` (not cluster-scoped `cluster`).
- Trust-manager and other addons may use cluster singleton — always read EP/CRD CEL rules; do not assume.

### Status conditions

- Use `common.HandleReconcileResult()` for Ready/Degraded state machine.
- Pair implementation tasks with e2e assertions on `Ready` condition (CM-546 lesson).

### OLM / packaging

- When adding new owned CRD to bundle, plan must include N-1 → N upgrade verification (CM-770 lesson).

### Operand versions

- Bindata version pins must align with platform compatibility matrix (OSSM/Istio) — CM-521 lesson.

## Round 2 — Network Policy (CM-802 / CM-525)

### Dual controller paths (cert-manager core)

- **cert-manager core** uses library-go `static-resources-controller` for default/static NetworkPolicies.
- **User-defined** `networkPolicies[]` use a dedicated runtime reconciler under `pkg/controller/certmanager/`.
- Do not apply addon controller-runtime SSA patterns to library-go static NP management.

### Reconcile discipline (CM-758, CM-763, CM-764)

- Static NPs: verify library-go `ApplyNetworkPolicy` corrects spec drift (tamper e2e).
- User-defined NPs: **compare before update** — never unconditional update (CM-763).
- User-defined NPs: **Watches** on `NetworkPolicy` for delete → prompt recreate (CM-764).

### Backward compatibility

- `defaultNetworkPolicy` defaults **false** — opt-in only.
