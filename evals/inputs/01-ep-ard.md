# Input: EP / ARD — cert-manager Network Policies

**Link:** https://github.com/openshift/enhancements/blob/master/enhancements/cert-manager/cert-manager-network-policies.md

**Tracking:** CM-624 | **Authors:** @manpilla | **Last updated:** 2025-09-25

## Summary

Implement fine-grained Kubernetes NetworkPolicy objects for cert-manager operator (OLM bundle) and operands (operator-managed). Opt-in via `defaultNetworkPolicy` on CertManager CR for backward compatibility.

## Key design points

- **Operator NP:** Managed by OLM bundle (not operator reconcile loop)
- **Operand NP:** Operator creates deny-all + baseline allow rules when `defaultNetworkPolicy: "true"`
- **User-configurable:** `networkPolicies[]` on CertManager spec for additional cert-manager egress rules
- **istio-csr NP:** Automatically managed by operator; no user configuration
- **Non-goals:** No AdminNetworkPolicy; no generic cluster-wide policy solution; no user config for istio-csr NP
- **Components:** cert-manager, webhook, cainjector, istio-csr — traffic matrix in EP (API server 6443, DNS, metrics 9402, webhook 10250, istio gRPC)

## API fields

- `defaultNetworkPolicy` (default false) — opt-in
- `networkPolicies[]` — user-defined rules per componentName

## Controllers (implementation)

- Static/default policies via static-resources-controller (library-go)
- User-defined policies via dedicated user-defined network policy controller

## Risks / constraints

- Breaking cert issuance if egress too restrictive without user-defined rules
- Monitoring must still scrape metrics
- Webhook must remain reachable from API server
