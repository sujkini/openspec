# Input: Jira Epics — CM-802 (operator) + CM-525 (operand)

## CM-802 — Operator epic

**Link:** https://issues.redhat.com/browse/CM-802

**Summary:** Tailored Network Policies for cert-manager - Operator

**Context:** Red Hat Product Security mandate — ship NetworkPolicies with OpenShift operators. Supports OCPSTRAT-819.

**Goals (cert-manager):**

1. Identify affected components
2. Characterize allowed/required traffic
3. Specify NetworkPolicy to limit traffic
4. Implement in targeted OpenShift release

**Requirements:** Implement network policies restricting ingress and egress. AdminNetworkPolicy considered but not required.

## CM-525 — Operand epic

**Link:** https://issues.redhat.com/browse/CM-525

**Summary:** Tailored Network Policies for cert-manager (operand scope)

Same security mandate and goals as CM-802; operand-focused implementation (CertManager CR fields, default + user-defined policies).

**Strategy link:** OCPSTRAT-819
