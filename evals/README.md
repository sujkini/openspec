# Eval pipeline — retrospective workflow improvement

Continuous improvement loop for **openspec-agile-workflow**: derive evals from completed feature bundles (EP + epic + stories + PRs + bugs), refine templates in place, and accumulate learnings for the next bundle.

## One command, one feature bundle

```
Paste inputs → /eval-loop → baseline updated → paste next bundle → /eval-loop again
```

| Step | Action |
|------|--------|
| 1 | Fill `evals/inputs/` with one feature bundle (links + exports) |
| 2 | Run **`/eval-loop`** in Cursor |
| 3 | Review `evals/baseline/` (cumulative evals + changelog) |
| 4 | Replace `evals/inputs/` with the next feature bundle |
| 5 | Run **`/eval-loop`** again — prior evals and refined templates are auto-loaded |

## Data flow

```
evals/inputs/  ──────────────────►  Epic Bug Analysis  ──►  evals/outputs/epic-bug-analysis/*
                                              │
templates (schema path)  ─────────┐          │
baseline/evals/  ────────────────┤          ▼
baseline/agents.md  ─────────────┴────►  Eval Generation
                                              │
                                              ├──► evals/baseline/evals/  (cumulative)
                                              ├──► PATCH templates in schema path
                                              └──► evals/baseline/agents.md
```

**Round 2+:** Eval Generation reads the **same template paths** — already updated from the previous loop.

## Template source of truth

Eval Generation always reads and writes templates at:

| Context | Path |
|---------|------|
| This distribution repo | `schemas/openspec-agile-workflow/templates/` |
| Installed project | `openspec/schemas/openspec-agile-workflow/templates/` |

Do **not** maintain a separate template copy under `baseline/`. Only `baseline/refinement-changelog.md` records what changed.

## Directory layout

| Path | Purpose |
|------|---------|
| `inputs/` | Generic placeholders — replace each round |
| `outputs/epic-bug-analysis/` | Current round RCA artifacts |
| `outputs/eval-generation/` | Current round eval drafts + gap analysis |
| `baseline/evals/` | **Cumulative** eval cases (all rounds) |
| `baseline/evals-registry.yaml` | Master index |
| `baseline/agents.md` | Refined agent routing (updated each loop if needed) |
| `baseline/rounds/round-N/` | Snapshot per completed loop |
| `epic-bug-analysis/SYSTEM_PROMPT.md` | Epic Bug Analysis agent instructions |
| `eval-generation/SYSTEM_PROMPT.md` | Eval Generation agent instructions |
| `round-state.yaml` | Current round number |

## Inputs (paste each round)

| File | Content |
|------|---------|
| `inputs/feature-meta.yaml` | Optional label (feature name, epic key) |
| `inputs/01-ep-ard.md` | EP / ARD link + content |
| `inputs/02-jira-epic.md` | Epic export |
| `inputs/03-original-repo.md` | Pre-feature repo commit/branch |
| `inputs/04-user-stories.md` | User stories |
| `inputs/05-repo-prs.md` | PR links for this EP |
| `inputs/bugs/index.yaml` | Bug keys list |
| `inputs/bugs/*.md` | One file per bug |

## Eval Generation stages

Evals are created/updated for: **repo-assessment → constitution → plan → tasks → implementation**.

**validation.md** is refined in place (it *is* the spec-stage eval) — not duplicated under `baseline/evals/`.
