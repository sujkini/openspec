# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation.

This repo is the **distribution package**: schema, templates, Cursor commands, and optional eval tooling. You install it into your own project with `install.sh`.

---

## What is openspec-agile-workflow?

A structured workflow that turns a Jira ticket into reviewed artifacts, then implements them **task-by-task** on your fork using [OAPE](https://github.com/openshift-eng/oape-ai-e2e) commands.

### Pipeline

```
validation → specs → repo-assessment + constitution → plan → tasks → implementation → archive
```

| Stage | Artifacts | Purpose |
|-------|-----------|---------|
| **Spec understanding** | `validation.json`, `specs.md` | Validate and refine the Jira spec before any repo work |
| **Repo understanding** | `repo-assessment.md`, `constitution.md` | Ground planning in the target repository |
| **Planning** | `plan.md` | Phased implementation plan (§0–§8) |
| **Task creation** | `tasks.md` | Executable task manifest with assigned agents |
| **Implementation** | code on fork + `implementation-report.md` | Task-by-task OAPE execution with per-task approval |
| **Archive** | archived change | Close out the change |

### Gates on every artifact

After each artifact is generated:

```
generate v1 → run stage evals → refine artifact → user approve → next stage
```

If you **reject** with feedback, only the **current** artifact is regenerated. Previously approved artifacts stay **immutable**.

During **implementation**, approval happens **after every task** (not per phase).

---

## What you need to run it

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | `npm install -g @fission-ai/openspec` |
| [Cursor](https://cursor.com) | Slash commands and skills install to `.cursor/` |
| Jira access | Ticket key at `/opsx-new`; spec via MCP or paste into `inputs/jira-spec.md` |
| Target GitHub repo | URL before **repo-assessment** (`inputs/jira.yaml` → `target_repo`) |
| Fork GitHub repo | URL before **`/opsx-apply`** (`inputs/jira.yaml` → `fork_repo_url`) |
| `AGENTS.md` in target repo | **Expected in production** — see [agents.md](#agentsmd-testing-only) below |

### Required after install (forward workflow)

These are installed by `install.sh` and are **required** for `/opsx-new` through `/opsx-apply`:

```
openspec/
├── config.yaml                              # selects openspec-agile-workflow schema
├── changes/                                 # one folder per change
└── schemas/openspec-agile-workflow/
    ├── schema.yaml                          # workflow definition
    ├── templates/                           # artifact templates
    ├── evals/                               # stage evals for /opsx-continue
    ├── stage-gate/                          # eval + feedback prompts
    └── agents.md                            # bundled roster (testing only — see below)

.cursor/
├── commands/                                # opsx-*, OAPE commands
└── skills/                                  # workflow skills
```

### Optional (retrospective eval loop)

```
evals/                                       # only needed for /eval-loop
```

The forward workflow does **not** require `evals/` at project root. Stage evals for `/opsx-continue` ship inside the schema package.

---

## Install with `install.sh`

`install.sh` copies everything needed to run **openspec-agile-workflow** into a target project. It is the supported install path — **`openspec init` alone** installs the default `spec-driven` schema, not this workflow.

```bash
git clone https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-project
```

Or install into the current directory:

```bash
./install.sh .
```

**Restart Cursor** after install so slash commands load.

### What `install.sh` does (step by step)

1. **Checks** that the `openspec` CLI is installed.
2. **Runs `openspec init --tools cursor`** if `openspec/` does not exist (creates the OpenSpec skeleton).
3. **Creates** `openspec/changes/` if missing.
4. **Copies the full schema package** from `schemas/openspec-agile-workflow/` → `openspec/schemas/openspec-agile-workflow/` (schema, templates, stage evals, stage-gate prompts).
5. **Copies `agents.md`** from this repo root into `openspec/schemas/openspec-agile-workflow/agents.md` (cert-manager-operator roster for testing — see below).
6. **Copies `config.yaml.example`** → `openspec/config.yaml` (selects this schema and artifact rules).
7. **Copies all Cursor commands** from `tooling/cursor/commands/` → `.cursor/commands/` (15 files: opsx-new, opsx-continue, opsx-apply, OAPE commands, eval-loop, etc.).
8. **Copies all Cursor skills** from `tooling/cursor/skills/` → `.cursor/skills/`.
9. **Copies `evals/`** → project `evals/` (optional retrospective pipeline for `/eval-loop`; preserves existing baseline if re-run).
10. **Validates** the schema with `openspec schema validate openspec-agile-workflow`.

### Install map

| Source (this repo) | Target (your project) |
|--------------------|-------------------------|
| `schemas/openspec-agile-workflow/` | `openspec/schemas/openspec-agile-workflow/` |
| `agents.md` | `openspec/schemas/openspec-agile-workflow/agents.md` |
| `config.yaml.example` | `openspec/config.yaml` |
| `tooling/cursor/commands/` | `.cursor/commands/` (all command files) |
| `tooling/cursor/skills/` | `.cursor/skills/` |
| `evals/` | `evals/` (optional — `/eval-loop` only) |

### Re-installing

- **`openspec update`** overwrites `.cursor/` with stock OpenSpec commands. Re-run `install.sh` to restore this workflow's commands.
- Re-running `install.sh` is safe: it refreshes the schema and commands; existing changes under `openspec/changes/` are preserved.

---

## agents.md (testing only)

This distribution repo ships **`agents.md`** inside the schema package for **testing and development** against the [cert-manager-operator](https://github.com/openshift/cert-manager-operator) repository. It defines:

- Agent IDs (e.g. `API_Agent`, `OperatorController_Agent`, `Testing_Agent`)
- Execution routing to OAPE commands
- Repo-specific conventions for that operator

**It is cert-manager-operator specific.** Do not treat it as a generic agent roster for other projects.

### Where agents are resolved (lookup order)

When the workflow needs agent routing (repo-assessment onward):

1. `openspec/changes/<change>/inputs/AGENTS.md` (change-local override)
2. `openspec/changes/<change>/inputs/agents.md`
3. `{target_repo}/AGENTS.md` ← **expected long-term location**
4. `{target_repo}/agents.md`
5. `{schema_root}/agents.md` ← bundled testing copy from install

If none are found, the agent asks you once to provide `AGENTS.md`. If you decline, the workflow continues in **PROVISIONAL** mode (documented in constitution, plan, and tasks).

**Production expectation:** your target repository should own its `AGENTS.md`. The bundled copy is a fallback so you can run the workflow end-to-end before the target repo has one.

---

## Cursor commands

### Forward workflow (required)

| Command | Purpose |
|---------|---------|
| `/opsx-new CM-830` | Start a change from a Jira key; writes `inputs/jira.yaml` |
| `/opsx-continue` | Create the next artifact; runs stage evals; asks for approval |
| `/opsx-apply` | Implement tasks on your fork — **one task at a time**, user approval after each |
| `/opsx-archive` | Archive a completed change |
| `/opsx-explore` | Explore ideas without creating artifacts |

### OAPE commands (used during `/opsx-apply`)

Only these OAPE commands are invoked during implementation (one per task):

| Command | When |
|---------|------|
| `/oape:api-generate` | API_Agent task (non-verification) |
| `/oape:api-generate-tests` | API_Agent verification-only task |
| `/oape:api-implement` | OperatorController_Agent task |
| `/oape:e2e-generate` | E2E / Testing_Agent task |

Other OAPE commands (`review`, `predict-regressions`, etc.) are **not** used during `/opsx-apply`.

### Retrospective eval loop (optional)

| Command | Purpose |
|---------|---------|
| `/eval-loop` | Improve evals and templates from a **completed** feature bundle |

---

## Step-by-step example (forward workflow)

```
/opsx-new CM-830
/opsx-continue    → validation.json              [approve]
/opsx-continue    → specs.md                     [approve]
/opsx-continue    → repo-assessment + constitution [approve]
/opsx-continue    → plan.md                      [approve]
/opsx-continue    → tasks.md                     [approve]
/opsx-apply       → task T1 [approve] → task T2 [approve] → … → draft PR
/opsx-archive
```

### Inputs during a change

| Input | When required |
|-------|----------------|
| Jira ticket key | `/opsx-new` |
| Jira spec content | Paste into `inputs/jira-spec.md` or use Jira MCP |
| Target repo URL | Before **repo-assessment** — agent prompts if empty (`inputs/jira.yaml` → `target_repo`) |
| Fork repo URL | Before **`/opsx-apply`** (`inputs/jira.yaml` → `fork_repo_url`) |
| `AGENTS.md` | Before repo-assessment/plan/tasks if not in target repo — see [agents.md](#agentsmd-testing-only) |

---

## Implementation (`/opsx-apply`)

Implementation follows **`tasks.md`** in linear execution order, respecting task dependencies.

For **each pending task**:

1. Compose `implementation/design-bundle.md` scoped to **that task only**
2. Resolve **exactly one** allowed OAPE command (or manual work for non-OAPE agents)
3. Run the command in your **fork** working copy
4. Verify against the task's acceptance criteria
5. Present a task summary and ask for **user approval**
6. On approve: mark task `- [x]`, log progress, move to next task
7. On reject: add revision feedback, re-run **current task only**

When all tasks are done: commit, push feature branch, open a **draft PR** on your fork.

Typical task chain for a full feature:

```
T1  api-generate        → API types / CRD scaffolding
T2  api-generate-tests  → .testsuite.yaml integration tests
T3  api-implement       → controller / operator logic
T4  e2e-generate        → end-to-end tests (when applicable)
```

---

## Two different eval systems

Do not confuse these — they serve different purposes.

### 1. Forward workflow eval gate (`/opsx-continue`)

**When:** After each artifact is generated during a live change.

**Where:** Stage evals in `openspec/schemas/openspec-agile-workflow/evals/*_eval.yaml`

**What happens:**

```
generate artifact → score against stage evals → refine artifact → user approve
```

Templates under `openspec/schemas/.../templates/` are **not** modified. Only the change artifact is refined.

### 2. Retrospective eval loop (`/eval-loop`)

**When:** After a feature is **fully completed** (EP, epic, stories, PRs, bugs). Used to improve the workflow itself over time.

**Where:** Project-root `evals/` directory (installed optionally by `install.sh`)

**What happens:**

```
Paste feature bundle into evals/inputs/ → /eval-loop → baseline updated → repeat with next bundle
```

One command runs the full loop:

1. Validate `evals/inputs/` (no placeholder files)
2. Load prior baseline and refined templates (round 2+)
3. **Epic Bug Analysis** → `evals/outputs/epic-bug-analysis/`
4. **Eval Generation** → merge eval cases, refine templates, sync stage evals
5. Update `evals/baseline/` and round state

| Step | You do |
|------|--------|
| 1 | Fill all files under `evals/inputs/` with one completed feature (EP, epic, stories, PRs, bugs) |
| 2 | Run **`/eval-loop`** in Cursor |
| 3 | Review `evals/baseline/` and `evals/refined-templates/` |
| 4 | Replace `evals/inputs/` with the next feature bundle |
| 5 | Run **`/eval-loop`** again — prior evals and refined templates feed the next round |

Eval workflow templates are read/written at `evals/refined-templates/` — **not** `schemas/.../templates/`. See `evals/README.md` for file layout and input format.

---

## Validate schema

```bash
openspec schema validate openspec-agile-workflow
```

Run from a project where the schema is installed under `openspec/schemas/`.

---

## Repository layout (this distribution repo)

```
agents.md                          # cert-manager-operator roster (copied into schema on install)
config.yaml.example                # → openspec/config.yaml
install.sh                         # install into another project
schemas/openspec-agile-workflow/
├── schema.yaml                    # workflow definition
├── agents.md                      # synced copy for schema package
├── templates/                     # artifact templates (forward workflow)
├── evals/                         # stage evals (forward workflow gate)
└── stage-gate/                    # SYSTEM_PROMPT, USER_FEEDBACK_PROMPT, artifact map
evals/                             # retrospective eval loop (/eval-loop)
├── inputs/                        # paste one feature bundle at a time
├── baseline/                      # cumulative evals + changelog
├── epic-bug-analysis/
└── eval-generation/
tooling/cursor/
├── commands/                      # opsx-new, opsx-continue, opsx-apply, OAPE, eval-loop
└── skills/
```

---

## Important notes

- Use **`install.sh`**, not `openspec init` alone, to get this workflow.
- **`openspec update`** overwrites `.cursor/` — re-run `install.sh` afterward.
- Bundled **`agents.md`** is for **testing** cert-manager-operator; production repos should provide their own `AGENTS.md`.
- Implementation edits go to your **fork**, not the upstream target repo.
- Rejecting an artifact regenerates **only that artifact**; approved artifacts are never modified.

---

## License

MIT (schema and templates). OpenSpec CLI is separate — see [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec).
