# Input: User stories — Network Policy (CM-802 / CM-525)

**Strategy:** OCPSTRAT-819

## EP user stories

- Administrator: cert-manager components cannot talk to unrelated workloads
- Security engineer: default-deny with explicit allows only
- SRE: Prometheus can still scrape metrics
- cert-manager user: issuance/webhook still work after policies applied

## Implementation stories (from PR traceability)

| Key / PR | Story theme |
|----------|-------------|
| CM-577 / PR #320, #335 | Core NetworkPolicy implementation for operands |
| CM-525 / PR #348 | NP support scoped to CoreController component |
| CM-802 | Operator-side / OLM bundle policies (epic umbrella) |
| CM-758 / PR #338, #340 | library-go bump — static NP reconcile on spec drift |
| CM-763 / PR #339 | Fix unconditional update loop in user-defined NP controller |
| CM-764 / PR #342, #343 | Add NetworkPolicy informer for user-defined NP delete/recreate |

## EP → story gaps (from bugs)

| Gap | Bug |
|-----|-----|
| Watch/reconcile when static NP spec tampered | CM-758 |
| No-op update detection for user-defined NP | CM-763 |
| Immediate recreate on user-defined NP delete | CM-764 |
