# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema: gated, Jira-driven spec-first workflow for AI-assisted development.

**Pipeline:**

```
validation → specs → repo-assessment + constitution → plan → tasks → implementation → archive
```

Each artifact has a **user approval gate**. Implementation runs phase-by-phase on your fork and opens a **draft PR** when done.

## Prerequisites

- [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec): `npm install -g @fission-ai/openspec`
- [Cursor](https://cursor.com) (or another supported IDE)

## Install into your project

```bash
git clone https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-project
```

Restart Cursor after install.

## Usage

| Command | Purpose |
|---------|---------|
| `/opsx-new CM-830` | Start change from Jira key; writes `inputs/jira.yaml` |
| `/opsx-continue` | Create next artifact (validation → specs → … → tasks) |
| `/opsx-apply` | Implement tasks on your fork (per-phase approval) |
| `/opsx-archive` | Archive completed change |
| `/opsx-explore` | Think through ideas (no artifacts) |
| `/eval-loop` | Retrospective eval loop for one feature bundle (see below) |

**Step-by-step example:**

```
/opsx-new CM-830
/opsx-continue    → validation.json   [approve]
/opsx-continue    → specs.md          [approve]
/opsx-continue    → repo-assessment + constitution [approve]
/opsx-continue    → plan.md           [approve]
/opsx-continue    → tasks.md          [approve]
/opsx-apply       → code on fork + draft PR
/opsx-archive
```

## What gets installed

| Source (this repo) | Target (your project) |
|--------------------|------------------------|
| `schemas/openspec-agile-workflow/` | `openspec/schemas/openspec-agile-workflow/` |
| `config.yaml.example` | `openspec/config.yaml` |
| `tooling/cursor/commands/` | `.cursor/commands/` |
| `tooling/cursor/skills/` | `.cursor/skills/` |
| `evals/` | `evals/` |

## Eval pipeline (`/eval-loop`)

Improve templates and accumulate evals from **completed** features (EP + epic + stories + PRs + bugs).

```
Paste bundle → /eval-loop → baseline updated → paste next bundle → /eval-loop
```

1. Fill generic placeholders in `evals/inputs/` (one feature at a time)
2. Run **`/eval-loop`** — Epic Bug Analysis → Eval Generation (refine templates in place)
3. Review `evals/baseline/` (cumulative evals, changelog)
4. Replace `evals/inputs/` and run **`/eval-loop`** again — prior evals and refined templates feed the next round

Templates are read/written at `schemas/openspec-agile-workflow/templates/` (or `openspec/schemas/...` when installed). See `evals/README.md`.

## Inputs during a change

| Input | When required |
|-------|----------------|
| Jira ticket key | `/opsx-new` |
| Jira spec content | Paste into `inputs/jira-spec.md` or use Jira MCP |
| Target repo URL | Before **repo-assessment** — agent **prompts if empty** (`inputs/jira.yaml` → `target_repo`) |
| Fork repo URL | Before `/opsx-apply` (`inputs/jira.yaml` → `fork_repo_url`) |

## Validate schema

```bash
openspec schema validate openspec-agile-workflow
```

## Repository layout

```
schemas/openspec-agile-workflow/
├── schema.yaml
└── templates/
evals/
├── inputs/       # generic placeholders — paste each feature bundle
├── baseline/     # cumulative evals + feedback loop
└── epic-bug-analysis/ eval-generation/
tooling/cursor/
├── commands/     # opsx-new, opsx-continue, eval-loop, ...
└── skills/
config.yaml.example
install.sh
```

## Important notes

- **`openspec update` overwrites `.cursor/`** with stock OpenSpec commands. Re-run `install.sh` to restore this workflow's commands.
- **`openspec init` alone** installs the default `spec-driven` schema and core commands — use **`install.sh`** for this workflow.
- Implementation creates a **feature branch** on your fork and opens a **draft PR** to the fork's default branch (`master`/`main`).

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
