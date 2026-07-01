# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation.

Clone this repo, edit two files for your operator, and start working. No install script needed.

---

## Getting Started

### 1. Install OpenSpec CLI

```bash
npm install -g @fission-ai/openspec
```

The CLI is required at runtime for `/opsx-continue` (`openspec status`, `openspec instructions`).

### 2. Clone

```bash
git clone -b openspec-operator-generic https://github.com/sujkini/openspec.git
cd openspec
```

**Restart Cursor** after cloning so slash commands load from `.cursor/commands/`.

### 3. Customize for your operator (2 files)

Edit these files in `openspec/inputs/`:

| File | What to define |
|------|---------------|
| **`inputs/agents.md`** | Agent routing, repository architecture, test patterns, verification matrix |
| **`inputs/constitution.md`** | Coding guardrails, CI gates, governance rules |

These are the **only operator-specific files**. Everything else is generic.

Your `agents.md` should define:

- **Repository layout** — directory structure, key packages
- **Architecture patterns** — controller frameworks, reconciliation flow
- **Test exemplar** — how tests are structured (mocks, table-driven patterns, file naming)
- **Execution agent routing** — agent IDs and which paths/packages they own
- **Per-task verification matrix** — `make` targets and `go test` commands per task type

The bundled `agents.md` ships with **cert-manager-operator** as a reference. Replace it entirely with your operator's documentation.

### 4. Generate evals (optional, recommended)

To improve workflow quality over time, provide data from a **completed feature** in `eval-generation/input/feature-bundle.yaml`:

```bash
vi eval-generation/input/feature-bundle.yaml
```

Fill in: feature name, epic key, target repo, Enhancement Proposal content, Jira epic, repo state, user stories, PR diffs, and bugs. Then run:

```
/eval-loop
```

This generates eval cases that the forward workflow (`/opsx-continue`, `/opsx-apply`) uses as quality gates. Repeat with each completed feature to accumulate better evals.

### 5. Start a change

```
/opsx-new PROJ-123
```

You have **two modes**:

#### Mode A: Working-folder mode (local code changes)

Use when your Cursor workspace IS the operator repo.

When prompted for target repo, tell the agent: **"use this as the working directory"**

- Code changes happen directly in your working directory
- No fork URL needed, no draft PR

#### Mode B: Fork mode (draft PR)

When prompted, provide:
- **Target repo URL** — before repo-assessment
- **Fork repo URL** — before `/opsx-apply`

The agent clones your fork, implements task-by-task, and opens a draft PR.

### 6. Run the workflow

```
/opsx-new PROJ-123          → start change from Jira ticket
/opsx-continue              → validation.json      [approve]
/opsx-continue              → specs.md             [approve]
/opsx-continue              → repo-assessment.md   [approve] (constitution.md resolved as input)
/opsx-continue              → plan.md              [approve]
/opsx-continue              → tasks.md             [approve]
/opsx-apply                 → task T1 [approve] → task T2 [approve] → … → done
/opsx-archive               → archive the change
```

You can also start from an **Enhancement Proposal** file instead of a Jira key — just tell the agent the path.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | `npm install -g @fission-ai/openspec` (needed at runtime for `openspec status`, `openspec instructions`) |
| [Cursor](https://cursor.com) | Slash commands load from `.cursor/commands/` |
| Jira access | Ticket key at `/opsx-new`; spec via MCP or paste |
| Target GitHub repo | URL before **repo-assessment**; **or** use working-folder mode |
| Fork GitHub repo | URL before **`/opsx-apply`**; **skip in working-folder mode** |

---

## Repository Layout

```
.
├── openspec/                              # Pre-built — ready to use after clone
│   ├── config.yaml                        # Workflow configuration and flags
│   ├── inputs/                            # Operator-specific inputs (edit these)
│   │   ├── agents.md                      # Agent routing, architecture, test patterns
│   │   └── constitution.md                # Coding guardrails, CI gates, governance
│   ├── schemas/openspec-agile-workflow/   # Schema, templates, stage-gate, evals
│   │   ├── schema.yaml                    # Workflow definition
│   │   ├── agents.md                      # Bundled agents.md (fallback)
│   │   ├── templates/                     # Generic artifact templates (*-template.md)
│   │   ├── evals/                         # Stage eval results (forward workflow gate)
│   │   ├── stage-gate/                    # Eval gate prompts and artifact map
│   │   └── feedback_stage_artifacts/      # Format spec for rejection rounds
│   └── changes/                           # Active changes (created per /opsx-new)
├── .cursor/                               # Pre-built — Cursor loads immediately
│   ├── commands/                          # opsx-new, opsx-continue, opsx-apply, OAPE, eval-loop
│   ├── skills/                            # openspec-*, effective-go, e2e-test-generator
│   └── e2e-test-generator/                # Fixtures for /oape:e2e-generate
├── eval-generation/                       # Optional retrospective eval loop
│   ├── input/                             # Single feature-bundle.yaml
│   ├── output-evals/                      # Stage-wise cumulative eval results
│   ├── output-refined-templates/          # Working copy + output (seeded → patched each round)
│   └── eval-generation-workflow/          # Internal workflow machinery
│       ├── template-gaps/                 # Gap reports per template + agents.md
│       ├── outputs/                       # Epic-bug-analysis + patches
│       ├── rounds/                        # Round snapshots
│       └── generation-phase/              # SYSTEM_PROMPT, template-inventory
└── README.md
```

---

## Configuration (`openspec/config.yaml`)

Key flags you can tune:

```yaml
flags:
  max_feedback_rounds: 3
  exit_on_all_tasks_complete: true
```

| Flag | Default | What it does |
|------|---------|--------------|
| `max_feedback_rounds` | 3 | Max rejection + refinement loops per artifact before halting |
| `exit_on_all_tasks_complete` | true | Auto-exit implementation when all tasks marked `[x]` |

The `rules:` section defines per-stage constraints. You generally don't need to edit these.

---

## What is openspec-agile-workflow?

A structured workflow that turns a Jira ticket into reviewed artifacts, then implements them **task-by-task** using [OAPE](https://github.com/openshift-eng/oape-ai-e2e) commands.

### Pipeline

```
validation → specs → repo-assessment → [resolve constitution.md] → plan → tasks → implementation → archive
```

| Stage | Artifacts | Purpose |
|-------|-----------|---------|
| **Spec understanding** | `validation.json`, `specs.md` | Validate Jira spec before repo work |
| **Repo understanding** | `repo-assessment.md` | Ground planning in the target repository |
| **Constitution (input)** | `constitution.md` (resolved) | Non-negotiable guardrails |
| **Planning** | `plan.md` | Phased implementation plan |
| **Task creation** | `tasks.md` | Executable task manifest with agents |
| **Implementation** | code + `implementation-report.md` | Task-by-task execution with per-task approval |
| **Archive** | archived change | Close out |

### Gates on every artifact

```
generate v1 → run stage evals → refine → evaluation report → user approve → next stage
```

Every artifact gets an **evaluation report** showing eval pass/fail, gap analysis, and quality assessment.

If you **reject**, the agent refines and re-runs evals until you approve. Previously approved artifacts stay immutable.

---

## Cursor Commands

### Forward workflow

| Command | Purpose |
|---------|---------|
| `/opsx-new PROJ-123` | Start a change from a Jira key |
| `/opsx-continue` | Create next artifact; eval gate; approval |
| `/opsx-apply` | Implement tasks — one at a time, approval after each |
| `/opsx-archive` | Archive a completed change |
| `/opsx-explore` | Explore ideas without creating artifacts |

### OAPE commands (during `/opsx-apply`)

| Command | When |
|---------|------|
| `/oape:api-generate` | API_Agent task |
| `/oape:api-generate-tests` | API_Agent verification task |
| `/oape:api-implement` | OperatorController_Agent task |
| `/oape:e2e-generate` | E2E / Testing_Agent task |

### Retrospective eval loop (optional)

| Command | Purpose |
|---------|---------|
| `/eval-loop` | Improve evals from a completed feature bundle |

---

## Implementation (`/opsx-apply`)

For **each pending task**:

1. Compose `design-bundle.md` scoped to that task
2. Resolve one OAPE command (or manual work)
3. Run in fork working copy (or project cwd in working-folder mode)
4. Verify against acceptance criteria
5. Run **code-generation evals** → refine code (max 2 passes)
6. Present task summary + scorecard → **user approval**
7. On approve: write task report, mark task `[x]`, next task
8. On reject: re-run current task

When all tasks done: write `implementation-report.md`, commit, push, open draft PR.

---

## How the Eval Loop Works (`/eval-loop`)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed, feed its history into `/eval-loop` to generate eval cases that improve future runs.

### What to provide

Fill `eval-generation/input/feature-bundle.yaml` with data from **one completed feature**:

| Field | What to paste |
|-------|---------------|
| `feature_name` | Feature name |
| `epic_key` | Jira epic key |
| `target_repo` | Target repository URL |
| `enhancement_proposal` | Full EP/ARD content |
| `jira_epic` | Jira epic export |
| `repo_state` | Pre-feature repo state |
| `user_stories` | User stories linked to the epic |
| `repo_prs` | PR links and key diffs |
| `bugs` | Bug list with root causes |

### Running it

```
/eval-loop
```

### Where outputs go

| Location | What |
|----------|------|
| `eval-generation/output-evals/<stage>/<stage>_eval.yaml` | Eval cases per stage (cumulative) |
| `eval-generation/eval-generation-workflow/template-gaps/` | Gap reports per template and agents.md |
| `eval-generation/output-refined-templates/` | Refined templates (review and apply to sources) |
| `openspec/schemas/.../evals/*_eval.yaml` | Synced for forward workflow |

### Repeating

Update `eval-generation/input/feature-bundle.yaml` with the next completed feature and run `/eval-loop` again. Prior evals accumulate.

---

## agents.md — Operator-Specific Customization

### Where agents are resolved (lookup order)

1. `{target_repo}/AGENTS.md` — check target repo first
2. `{target_repo}/agents.md`
3. `openspec/inputs/agents.md` — project inputs/ folder
4. `{schema_root}/agents.md` — bundled copy

### Where constitution is resolved (lookup order)

1. `{target_repo}/constitution.md` — check target repo first
2. `{target_repo}/CONSTITUTION.md`
3. `openspec/inputs/constitution.md` — project inputs/ folder

If not found, the agent generates one using `templates/constitution-template.md` as a one-time step.

---

## Important Notes

- **No install.sh needed** — clone and it's ready
- **OpenSpec CLI** is only needed at runtime (`openspec status`, `openspec instructions`)
- **`agents.md`** + **`constitution.md`** are the only operator-specific files
- All templates are generic and work for any operator
- Implementation edits go to your **fork** (default) or **working folder** — not upstream
- Rejecting an artifact regenerates only that artifact (except `specs.md` — exits workflow)

---

## Validate Schema

```bash
openspec schema validate openspec-agile-workflow
```

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
