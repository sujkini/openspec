# Baseline — cumulative feedback loop store

Updated after each `/eval-loop`. Fed as input to Epic Bug Analysis and Eval Generation on subsequent rounds.

| Path | Purpose |
|------|---------|
| `evals/` | Cumulative eval cases (YAML) — **not** a template copy |
| `evals-registry.yaml` | Master index of all eval IDs across rounds |
| `agents.md` | Refined agent routing and conventions |
| `refinement-changelog.md` | Append-only log of template changes |
| `rounds/round-N/` | Snapshot per completed loop |

**Templates** are NOT stored here. Eval Generation reads/writes `schemas/openspec-agile-workflow/templates/` (or `openspec/schemas/...` when installed).
