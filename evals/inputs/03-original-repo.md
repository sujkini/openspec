# Input: Original repo version (before Network Policy feature)

**Repository:** https://github.com/openshift/cert-manager-operator

**Pre-feature reference:** `master` before NetworkPolicy implementation (CM-577 / CM-802).

**Enhancement tracking:** CM-624 (EP)

**Suggested pin:** Commit before merge of PR #320 (CM-577: Network Policy for Cert Manager Operand) — 2025-10-24.

**Post-implementation paths:**

- `pkg/controller/certmanager/networkpolicies.go` (user-defined controller)
- Static NP via library-go static-resources-controller
- CertManager CR: `defaultNetworkPolicy`, `networkPolicies[]`
- OLM bundle NP manifests for operator namespace
