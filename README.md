# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation. Supports two code-generation strategies: **ai-helpers** (OAPE command routing + eval gate) and **direct** (plain agent implementation).

---

## Quick Start

### 1. Clone & Install

```bash
rm -rf /tmp/openspec-workflow
git clone -b openspec-backend https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-operator-repo
```

This copies `openspec/`, `.cursor/`, `eval-generation/`, and `dashboard/` into your project, installs the OpenSpec CLI, and sets up dependencies. Use `--no-dashboard` to skip the dashboard.

### 2. Start the Dashboard

```bash
cd /path/to/your-operator-repo
./dashboard/start.sh
```

Installs deps on first run, starts the FastAPI backend (port 8000) and React frontend (port 5173). Open http://localhost:5173. The backend polls `openspec/changes/` for telemetry data written by `/opsx-*` commands. See `dashboard/README.md` for details.

### 3. Restart Cursor

Restart Cursor so slash commands load from `.cursor/commands/`.

### 4. Run your first change

```
/opsx-new PROJ-123
```

---

## Configuration

After installation, configure two files in `openspec/inputs/`:

| File | What to define |
|------|---------------|
| **`openspec/inputs/agents.md`** | Agent routing, repository architecture, test patterns, verification matrix |
| **`openspec/inputs/constitution.md`** | Coding guardrails, CI gates, governance rules |

These are the **only operator-specific files**. Everything else is generic.

Your `agents.md` should define:
- **Repository layout** — directory structure, key packages
- **Architecture patterns** — controller frameworks, reconciliation flow
- **Test exemplar** — how tests are structured (mocks, table-driven patterns, file naming)
- **Execution agent routing** — agent IDs and which paths/packages they own
- **Per-task verification matrix** — `make` targets and `go test` commands per task type

The bundled `agents.md` ships with a reference. Replace it entirely with your operator's documentation.

---

## Running the Workflow

### Start a change

```
/opsx-new PROJ-123
```

### Progress through artifacts

```
/opsx-continue              → validation.json      [approve]
/opsx-continue              → specs.md             [approve]
/opsx-continue              → repo-assessment.md   [approve] (constitution.md resolved as input)
/opsx-continue              → plan.md              [approve]
/opsx-continue              → tasks.md             [approve]
```

Each artifact is:
1. Generated from the template
2. Evaluated against stage evals
3. Refined if needed
4. Presented for your approval

If you **reject**, the agent refines and re-runs evals until you approve. Previously approved artifacts stay immutable.

### Implement tasks

```
/opsx-apply                 → task T1 [approve] → task T2 [approve] → … → done
```

The implementation flow depends on `codegen_mode` in `openspec/config.yaml`:

**ai-helpers mode** (`codegen_mode: ai-helpers`):
1. Compose `design-bundle.md` scoped to that task
2. Resolve one OAPE command (or manual work)
3. Run in fork working copy (or project cwd in working-folder mode)
4. Verify against acceptance criteria
5. Run code-generation evals → refine code (max 2 passes)
6. Present task summary + scorecard → user approval
7. On approve: mark task complete, next task

**direct mode** (`codegen_mode: direct`):
1. Read context files (agents.md, constitution.md, specs, plan, repo-assessment)
2. Implement code directly via FILE OPERATIONS
3. Verify against acceptance criteria
4. Present task summary → user approval
5. On approve: mark task complete, next task

### Archive

```
/opsx-archive               → archive the change
```

---

## Working Modes

### Mode A: Working-folder mode (local code changes)

Use when your Cursor workspace IS the operator repo.

When prompted for target repo, tell the agent: **"use this as the working directory"**
- Code changes happen directly in your working directory
- No fork URL needed, no draft PR

### Mode B: Fork mode (draft PR)

When prompted, provide:
- **Target repo URL** — before repo-assessment
- **Fork repo URL** — before `/opsx-apply`

The agent clones your fork, implements task-by-task, and opens a draft PR.

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

### OAPE commands (ai-helpers mode only, during `/opsx-apply`)

| Command | When |
|---------|------|
| `/oape:api-generate` | API_Agent task |
| `/oape:api-generate-tests` | API_Agent verification task |
| `/oape:api-implement` | OperatorController_Agent task |
| `/oape:e2e-generate` | E2E / Testing_Agent task |

These commands are **not used** when `codegen_mode: direct`.

### Retrospective eval loop

| Command | Purpose |
|---------|---------|
| `/eval-loop` | Improve evals from a completed feature bundle |

---

## Configuration (`openspec/config.yaml`)

Key flags you can tune:

```yaml
flags:
  codegen_mode: ai-helpers       # "ai-helpers" or "direct"
  max_feedback_rounds: 3
  exit_on_all_tasks_complete: true
```

| Flag | Default | What it does |
|------|---------|--------------|
| `codegen_mode` | `ai-helpers` | Code generation strategy: `ai-helpers` (OAPE commands + code eval gate) or `direct` (plain agent, no OAPE, no eval gate) |
| `max_feedback_rounds` | 3 | Max rejection + refinement loops per artifact before halting |
| `exit_on_all_tasks_complete` | true | Auto-exit implementation when all tasks marked `[x]` |

### Code generation modes

**`ai-helpers`** — For each task, composes a `design-bundle.md`, routes to specialized OAPE Cursor commands (`api-generate`, `api-implement`, `e2e-generate`), scores generated code via a code-generation eval gate, refines until evals pass, then asks for user approval.

**`direct`** — The Cursor agent reads context files directly, implements code via FILE OPERATIONS, verifies against acceptance criteria, and asks for user approval. No OAPE commands, no design bundles, no code eval gate. Simpler and faster for straightforward tasks.

---

## Eval Loop (Optional, Recommended)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed, feed its history into `/eval-loop` to generate eval cases that improve the quality of future runs.

### Step 1: Provide inputs

Fill `eval-generation/input/feature-bundle.yaml` with data from a **completed feature**:

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

### Step 2: Run the eval loop

```
/eval-loop
```

### Step 3: Review template gaps

Review the gap reports generated in:

```
eval-generation/eval-generation-workflow/template-gaps/
```

Each file (`repo-assessment-gaps.md`, `plan-gaps.md`, `tasks-gaps.md`, etc.) describes generic template deficiencies discovered from the analyzed feature — what classes of information the templates should require but currently don't.

### Step 4: Review refined templates

Find refined templates in:

```
eval-generation/output-refined-templates/
```

These are patched versions of the templates with the patchable gaps addressed.

### Step 5: Apply approved refinements

If you approve the refined templates, copy them into the active workflow:

```bash
cp eval-generation/output-refined-templates/*.md openspec/schemas/openspec-agile-workflow/templates/
```

These are the templates used by the OpenSpec workflow for all future artifact generation.

### Step 6: Evals are auto-synced

The generated evals in `eval-generation/output-evals/` are automatically copied to:

```
openspec/schemas/openspec-agile-workflow/evals/
```

These evals run as quality gates during `/opsx-continue` for every future artifact.

### Repeating

Update `eval-generation/input/feature-bundle.yaml` with the next completed feature and run `/eval-loop` again. Prior evals accumulate — each round improves coverage.

---

## Pipeline Overview

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
| **Implementation** | code + `implementation-report.md` | Task-by-task execution with per-task approval (ai-helpers or direct mode) |
| **Archive** | archived change | Close out |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| [Node.js](https://nodejs.org/) | For OpenSpec CLI installation |
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | Installed by `install.sh` |
| [Cursor](https://cursor.com) | Slash commands load from `.cursor/commands/` |
| Jira access | Ticket key at `/opsx-new`; spec via MCP or paste |
| Target GitHub repo | URL before **repo-assessment**; or use working-folder mode |
| Fork GitHub repo | URL before `/opsx-apply`; skip in working-folder mode |

---

## Repository Layout

```
.
├── openspec/                              # Pre-built — ready to use after install
│   ├── config.yaml                        # Workflow configuration and flags
│   ├── inputs/                            # Operator-specific inputs (edit these)
│   │   ├── agents.md                      # Agent routing, architecture, test patterns
│   │   └── constitution.md                # Coding guardrails, CI gates, governance
│   ├── schemas/openspec-agile-workflow/   # Schema, templates, stage-gate, evals
│   │   ├── schema.yaml                    # Workflow definition
│   │   ├── templates/                     # Generic artifact templates (*-template.md)
│   │   ├── evals/                         # Stage eval cases (quality gates)
│   │   ├── stage-gate/                    # Eval gate prompts and artifact map
│   │   └── feedback_stage_artifacts/      # Format spec for rejection rounds
│   └── changes/                           # Active changes (created per /opsx-new)
├── .cursor/                               # Pre-built — Cursor loads immediately
│   ├── commands/                          # opsx-new, opsx-continue, opsx-apply, eval-loop
│   └── skills/                            # openspec-*, effective-go, e2e-test-generator
├── eval-generation/                       # Retrospective eval loop
│   ├── input/                             # feature-bundle.yaml (your input)
│   ├── output-evals/                      # Generated evals per stage (auto-synced)
│   ├── output-refined-templates/          # Refined templates (review before applying)
│   └── eval-generation-workflow/          # Internal workflow machinery
│       ├── template-gaps/                 # Gap reports per template
│       ├── outputs/                       # Epic-bug-analysis + patches
│       ├── rounds/                        # Round snapshots
│       └── generation-phase/              # SYSTEM_PROMPT, template-inventory
├── dashboard/                             # Observability dashboard (optional)
│   ├── config.json                        # Dashboard configuration
│   ├── start.sh                           # One-command launcher
│   ├── src/                               # FastAPI backend (ingest + UI)
│   └── web/                               # React + TypeScript SPA
├── install.sh                             # Installer script
└── README.md
```

---

## agents.md Resolution (lookup order)

1. `{target_repo}/AGENTS.md`
2. `{target_repo}/agents.md`
3. `openspec/inputs/agents.md`
4. `{schema_root}/agents.md` (bundled fallback)

## constitution.md Resolution (lookup order)

1. `{target_repo}/constitution.md`
2. `{target_repo}/CONSTITUTION.md`
3. `openspec/inputs/constitution.md`

If not found, the agent generates one using `templates/constitution-template.md`.

---

## Validate Schema

```bash
openspec schema validate openspec-agile-workflow
```

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
