# OpenSpec Agile Workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation. Supports two execution strategies (**phase-iterative** and **one-shot**), two code-generation modes (**ai-helpers** and **direct**), per-phase Jira traceability, and a post-CI E2E test generation pipeline.

---

## Quick Start

### 1. Clone & Install

```bash
rm -rf /tmp/openspec-workflow
git clone -b openspec-v1-restructured https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-operator-repo
```

This copies `openspec/`, `.cursor/`, `eval-generation/`, `harness-evals/`, and `dashboard/` into your project, installs the OpenSpec CLI, and sets up dependencies. Use `--no-dashboard` to skip the dashboard.

### 2. Configure execution mode (`openspec/config.yaml`)

```yaml
# openspec/config.yaml
flags:
  codegen_mode: ai-helpers        # or: direct
  task_execution_mode: phase-iterative  # or: one-shot
  auto_approve: false             # true for fully autonomous runs
```

| Flag | Options | Purpose |
|------|---------|---------|
| `codegen_mode` | `ai-helpers` / `direct` | Code generation strategy |
| `task_execution_mode` | `phase-iterative` / `one-shot` | How tasks are grouped and PRs raised |
| `auto_approve` | `true` / `false` | Skip manual approval gates |

### 3. Add operator documentation (`harness-evals/harness-docs/`)

Place your operator's documentation in `harness-evals/harness-docs/`:

```bash
cp /path/to/your-docs/*.md harness-evals/harness-docs/
```

These docs (architecture guides, coding conventions, testing patterns) are used by `/opsx-constitute` to generate your constitution. Without them, `/opsx-constitute` will not proceed.

### 4. Start the Dashboard

```bash
cd /path/to/your-operator-repo
./dashboard/start.sh
```

Installs deps on first run, starts the FastAPI backend (port 8000) and React frontend (port 5173). Open http://localhost:5173. The backend polls `openspec/changes/` for telemetry data written by `/opsx-*` commands. See `dashboard/README.md` for details.

### 5. Restart Cursor

Restart Cursor so slash commands load from `.cursor/commands/`.

### 6. Run your first change

```
/opsx-new PROJ-123
```

---

## Task Execution Modes

### Phase-Iterative (default)

Tasks are executed one phase at a time. After each phase completes:
- A draft PR is raised scoped to that phase
- A Jira Story ticket is created for the phase (linked to the epic)
- The user can trigger `/opsx-e2e --phase N` after CI passes
- `/opsx-continue` generates next-phase tasks

### One-Shot

All tasks across all phases are executed sequentially in a single run. A single PR is raised at the end covering the entire implementation. After CI passes, trigger `/opsx-e2e` for the final PR.

---

## E2E Exclusion Policy

E2E phases and tasks are **excluded from OAPE planning, task generation, and code generation**. They are handled separately by the `/opsx-e2e` post-CI pipeline instead.

A phase or task is classified as e2e when any of these match:
- Assigned Agent is `Testing_Agent`
- Title/objective contains "e2e" or "end-to-end"
- Target files are under `test/` (e2e, ginkgo, integration paths)
- Acceptance criteria references `make test-e2e`

E2e coverage is still documented in `plan.md` §6 (Verification matrix) for reference but is never generated during `/opsx-apply`.

---

## E2E Test Generation (Post-CI)

After a phase or final PR is raised and CI passes, trigger the E2E pipeline:

```
/opsx-e2e <change-name> --phase N    # phase-iterative: specific phase
/opsx-e2e <change-name>              # one-shot: final PR
/opsx-e2e --pr <URL>                 # direct PR URL
```

The pipeline runs five stages, each with a user approval gate:

| Stage | Output | Description |
|-------|--------|-------------|
| Pre-analysis | `e2e-analysis.md` | Scoping analysis from PR diff + review comments |
| Test plan | `test-plan.md` | Full tiered plan (15–20 cases) with traceability |
| Consolidation | `revised-test-plan.md` | Journey consolidation to configured limit |
| Code generation | `*_test.go` | Executable Ginkgo/Go test code |
| Execute | Push + run | Commit tests to PR branch, optionally execute |

All artifacts are written to `openspec/changes/<name>/e2e/`.

---

## Jira Integration

### Per-Phase Jira Tickets (phase-iterative mode)

After tasks for a phase are approved, a Jira Story ticket is created:
- Linked to the epic from `inputs/jira.yaml`
- Summary: `[Phase N] <phase title>`
- Description includes phase goal, dependencies, target files, task manifest, and acceptance criteria
- Stored in `inputs/jira.yaml` → `plan_phases[]`

If Jira creation fails, the phase is marked `PENDING` and retried once at `/opsx-apply` start.

---

## Configuration

After installation, configure two files in `openspec/inputs/`:

| File | What to define |
|------|---------------|
| **`openspec/inputs/agents.md`** | Agent routing, repository architecture, test patterns, verification matrix |
| **`openspec/inputs/constitution.md`** | Coding guardrails, CI gates, governance rules |

And populate the `harness-evals/` directory:

| Directory | What to place |
|-----------|---------------|
| **`harness-evals/harness-docs/`** | Operator documentation (architecture guides, coding conventions, testing patterns). Used by `/opsx-constitute` to generate constitution.md |
| **`harness-evals/evals/`** | Stage eval cases (populated by `/eval-loop` or placed manually). Used as quality gates during `/opsx-continue` and `/opsx-apply` |

These are the **only operator-specific files**. Everything else is generic.

### Harness-Evals Structure

```
harness-evals/
├── harness-docs/                    # Operator documentation (sole source for /opsx-constitute)
│   ├── architecture.md              # System design, component relationships
│   ├── coding-conventions.md        # Style guides, patterns, naming
│   ├── testing-patterns.md          # Test strategies, exemplars, fixtures
│   └── ...                          # Any .md files — all are read
│
└── evals/                           # Stage eval cases (quality gates)
    ├── repo-assessment_eval.yaml    # Repo assessment scoring
    ├── plan_eval.yaml               # Plan quality scoring
    ├── tasks_eval.yaml              # Task breakdown scoring
    └── code-generation_eval.yaml    # Per-task code quality scoring
```

- **Evals are optional.** If not present, eval scoring is skipped and the workflow proceeds with verification/tests and user approval only.
- **Harness-docs are required for `/opsx-constitute`.** The command will stop if no documentation is found.
- **`/eval-loop` auto-syncs** generated evals to `harness-evals/evals/`.

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
/opsx-continue              → repo-assessment.md   [approve]
/opsx-continue              → plan.md              [approve] (requires constitution.md in inputs/)
/opsx-continue              → tasks.md             [approve] (+ Jira phase ticket in phase-iterative)
```

Each artifact is:
1. Generated from the template
2. Evaluated against stage evals (skipped if `harness-evals/evals/` has no eval file for that stage)
3. Refined if needed
4. Presented for your approval

If you **reject**, the agent refines and re-runs evals until you approve. Previously approved artifacts stay immutable.

### Implement tasks

```
/opsx-apply                 → task T1 [approve] → task T2 [approve] → … → phase PR → next phase
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

### Generate E2E tests (post-CI)

```
/opsx-e2e <change-name> --phase N
```

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
| `/opsx-constitute <url>` | Generate constitution.md from harness-docs + repo |
| `/opsx-new PROJ-123` | Start a change from a Jira key |
| `/opsx-continue` | Create next artifact; eval gate; approval |
| `/opsx-apply` | Implement tasks — one at a time, approval after each |
| `/opsx-e2e` | Generate E2E tests for a phase/final PR after CI passes |
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
  codegen_mode: ai-helpers              # "ai-helpers" or "direct"
  task_execution_mode: phase-iterative  # "phase-iterative" or "one-shot"
  auto_approve: false                   # true for autonomous execution
  max_feedback_rounds: 3
  exit_on_all_tasks_complete: true
```

| Flag | Default | What it does |
|------|---------|--------------|
| `codegen_mode` | `ai-helpers` | Code generation strategy: `ai-helpers` (OAPE commands + code eval gate) or `direct` (plain agent, no OAPE, no eval gate) |
| `task_execution_mode` | `phase-iterative` | `phase-iterative`: one phase at a time with per-phase PRs and Jira tickets. `one-shot`: all tasks in one run, single PR |
| `auto_approve` | `false` | When `true`, skip manual approval gates — tasks auto-approve after verification |
| `max_feedback_rounds` | `3` | Max rejection + refinement loops per artifact before halting |
| `exit_on_all_tasks_complete` | `true` | Auto-exit implementation when all tasks marked `[x]` |

### Code generation modes

**`ai-helpers`** — For each task, composes a `design-bundle.md`, routes to specialized OAPE Cursor commands (`api-generate`, `api-implement`, `e2e-generate`), scores generated code via a code-generation eval gate, refines until evals pass, then asks for user approval.

**`direct`** — The Cursor agent reads context files directly, implements code via FILE OPERATIONS, verifies against acceptance criteria, and asks for user approval. No OAPE commands, no design bundles, no code eval gate. Simpler and faster for straightforward tasks.

### Task execution modes

**`phase-iterative`** — Tasks are grouped by plan phase. After each phase completes: a draft PR is raised, a Jira Story ticket is created for the phase, and `/opsx-continue` generates next-phase tasks. E2E tests can be triggered per phase after CI passes.

**`one-shot`** — All tasks execute sequentially across all phases. A single draft PR is raised at the end. E2E tests are triggered once after the final CI passes.

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

The generated evals in `eval-generation/output-evals/` are automatically synced to:

```
harness-evals/evals/
```

These evals run as quality gates during `/opsx-continue` for every future artifact.

### Repeating

Update `eval-generation/input/feature-bundle.yaml` with the next completed feature and run `/eval-loop` again. Prior evals accumulate — each round improves coverage.

---

## Pipeline Overview

```
validation → specs → repo-assessment → [constitution.md required] → plan → tasks → implementation → [E2E] → archive
```

| Stage | Artifacts | Purpose |
|-------|-----------|---------|
| **Spec understanding** | `validation.json`, `specs.md` | Validate Jira spec before repo work |
| **Repo understanding** | `repo-assessment.md` | Ground planning in the target repository |
| **Constitution (input)** | `constitution.md` (from `inputs/`) | Non-negotiable guardrails |
| **Planning** | `plan.md` | Phased implementation plan (e2e phases excluded) |
| **Task creation** | `tasks.md` + Jira phase ticket | Executable task manifest with agents (e2e tasks excluded) |
| **Implementation** | code + `implementation-report.md` | Task-by-task execution with per-task approval |
| **E2E (post-CI)** | `e2e-analysis.md`, `test-plan.md`, `*_test.go` | E2E test generation triggered by `/opsx-e2e` |
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
├── harness-evals/                            # Operator-owned (evals + documentation)
│   ├── harness-docs/                         # Operator docs (read by /opsx-constitute)
│   └── evals/                                # Stage eval YAMLs (quality gates)
├── openspec/                                 # Pre-built — ready to use after install
│   ├── config.yaml                           # Workflow configuration and flags
│   ├── inputs/                               # Operator-specific inputs (edit these)
│   │   ├── agents.md                         # Agent routing, architecture, test patterns
│   │   └── constitution.md                   # Coding guardrails, CI gates, governance
│   ├── schemas/openspec-agile-workflow/      # Schema, templates, stage-gate
│   │   ├── schema.yaml                       # Workflow definition
│   │   ├── templates/                        # Generic artifact templates (*-template.md)
│   │   ├── e2e-workflow/                     # E2E test generation pipeline templates
│   │   │   ├── pre-analysis-gate.md          # PR scoping and approval gate
│   │   │   ├── test-plan-generation.md       # Tiered test plan + consolidation + code gen
│   │   │   └── qe-behaviour.md              # Project-specific QE context
│   │   ├── stage-gate/                       # Eval gate prompts and artifact map
│   │   └── feedback_stage_artifacts/         # Format spec for rejection rounds
│   ├── telemetry/                            # Telemetry collection (change metrics, reports)
│   └── changes/                              # Active changes (created per /opsx-new)
├── .cursor/                                  # Pre-built — Cursor loads immediately
│   ├── commands/                             # opsx-new, opsx-continue, opsx-apply, opsx-e2e, eval-loop
│   └── skills/                               # openspec-*, effective-go, e2e-test-generator
├── eval-generation/                          # Retrospective eval loop
│   ├── input/                                # feature-bundle.yaml (your input)
│   ├── output-evals/                         # Generated evals per stage (auto-synced to harness-evals/)
│   ├── output-refined-templates/             # Refined templates (review before applying)
│   └── eval-generation-workflow/             # Internal workflow machinery
│       ├── template-gaps/                    # Gap reports per template
│       ├── outputs/                          # Epic-bug-analysis + patches
│       ├── rounds/                           # Round snapshots
│       └── generation-phase/                 # SYSTEM_PROMPT, template-inventory
├── dashboard/                                # Observability dashboard (optional)
│   ├── config.json                           # Dashboard configuration
│   ├── start.sh                              # One-command launcher
│   ├── src/                                  # FastAPI backend (ingest + UI)
│   └── web/                                  # React + TypeScript SPA
├── install.sh                                # Installer script
└── README.md
```

---

## agents.md Resolution (lookup order)

1. `{target_repo}/AGENTS.md`
2. `{target_repo}/agents.md`
3. `openspec/inputs/agents.md`
4. `{schema_root}/agents.md` (bundled fallback)

## constitution.md Resolution

`constitution.md` is read from a single location:

```
openspec/inputs/constitution.md
```

If this file does not exist or is empty, the workflow **stops before planning** and prompts you to provide it.

**How to create it:**
- Run `/opsx-constitute <repo-url>` — reads documentation from `harness-evals/harness-docs/` and generates a constitution based on your operator's governance rules
- Or place a pre-existing `constitution.md` directly in `openspec/inputs/`

**Important:** `/opsx-constitute` requires documentation in `harness-evals/harness-docs/`. If that directory is empty, the command will stop and ask you to add your operator docs first.

The workflow will **never** auto-generate a constitution from a template.

---

## Validate Schema

```bash
openspec schema validate openspec-agile-workflow
```

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
