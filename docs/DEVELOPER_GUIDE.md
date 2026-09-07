# OpenSpec Developer Guide

A step-by-step guide for developers running a Jira ticket through the OpenSpec
agile workflow in Cursor. Read this once before your first change; if you use the
default **phase-iterative** mode, start with
[How phase-iterative mode works](#how-phase-iterative-mode-works-read-this-on-your-first-run).
Use the [command cheat sheet](#command-cheat-sheet) at the end as a quick reference.

---

## What you need before you start

| Requirement | Why |
|---|---|
| [Cursor](https://cursor.com) | Slash commands load from `.cursor/commands/` |
| Python 3 + `pip` | Telemetry hooks (`openspec.telemetry.*`) |
| Node.js + `npm` | OpenSpec CLI (`install.sh`) |
| `git` | Fork mode, PRs, archive |
| Jira access | Ticket content at `/opsx-new`; optional Story creation under Epics |
| GitHub access | Repo-assessment, implementation, PRs |
| Operator repo | The codebase you are changing (your Cursor workspace) |

Optional but recommended:

- **`agents.md`** at operator repo root — coding/test conventions
- **`harness-evals/constitution.md`** — run `/opsx-constitute` once to generate
- **`harness-evals/harness-docs/`** — operator docs fed into constitution
- **`qe-e2e/qe-behaviour.md`** — operator E2E deployment context (for `/opsx-e2e`)

---

## Step 1 — Install OpenSpec into your operator repo

From any machine with network access:

```bash
rm -rf /tmp/openspec-workflow
git clone -b main https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-operator-repo
```

What `install.sh` does:

1. Installs the OpenSpec CLI (`npm`)
2. Runs `openspec init` in your operator repo
3. Copies `openspec/`, `.cursor/`, and `eval-generation/` into the repo
4. Installs Python deps for telemetry (`pyyaml`, `tiktoken`)
5. Updates `.gitignore` (excludes ephemeral `openspec/changes/` working data)

**Restart Cursor** after install so slash commands appear.

---

## Step 2 — Configure `openspec/config.yaml`

Open `openspec/config.yaml` in your operator repo. Recommended defaults for most
developers:

```yaml
flags:
  codegen_mode: direct                 # plain agent implementation (no OAPE helpers)
  task_execution_mode: phase-iterative # one phase at a time; optional PR per phase
  auto_approve: false                  # you approve each artifact and each task's code
  pr_between_phases: optional
```

| Flag | Recommended | What it means |
|---|---|---|
| `codegen_mode` | `direct` | Agent edits files directly. Use `ai-helpers` only if your team uses OAPE commands. |
| `task_execution_mode` | `phase-iterative` | Plan phases map 1:1 to user stories; tasks and PRs are per phase. |
| `auto_approve` | `false` | You are prompted to approve every artifact (`/opsx-continue`) and every task's code (`/opsx-apply`). Phase approval, PR creation, and Jira Story creation are **never** auto-approved regardless of this flag. |

Fill credentials before implementation or E2E:

```yaml
credentials:
  jira:
    base_url: "https://issues.redhat.com"   # your Jira host
    username: "your-username"
    api_token: ""                           # Jira PAT — never commit the real token
  github:
    upstream_repo_url: ""   # e.g. https://github.com/openshift/my-operator
    fork_repo_url: ""       # e.g. https://github.com/you/my-operator-fork
    token: ""               # GitHub PAT (cross-repo PR creation)
  cluster:
    kubeconfig_path: ""     # absolute path — required for local E2E test execution
```

---

## How phase-iterative mode works (read this on your first run)

With the default **`phase-iterative`** setting, OpenSpec does **not** implement the whole
Epic in one go. It works **one user story at a time**, and you repeat the same cycle for
each phase in `plan.md`.

### Core idea: one phase = one user story = one PR = optional E2E

| Concept | What it means for you |
|---|---|
| **Phase** | One slice of work in `plan.md` — labeled **User Story US-01**, **US-02**, etc. |
| **`tasks.md`** | Generated for **one phase only** — not all phases at once |
| **`/opsx-apply`** | Implements that phase's tasks, then stops |
| **Jira Story prompt** | After you approve Phase N `tasks.md`, if you pasted an **Epic** at `/opsx-new`, the agent asks whether to **create a Jira Story** for that phase under the Epic (see below) |
| **PR prompt** | After Phase N implementation is approved, the agent **always asks** whether to raise a **draft PR** for that phase — it is **never** raised automatically |
| **`/opsx-e2e --phase N`** | Generates E2E tests for **that phase's user story and PR** — run once per phase, not once for the whole Epic |

### Typical loop (repeat for Phase 1, 2, 3, …)

```
/opsx-continue   →  tasks for Phase 1 (User Story US-01)
       ↓  you approve tasks.md
       ↓  [Epic input only] agent asks: "Create Jira Story [US-01] … under CM-800? (Yes / No)"
/opsx-apply      →  implement Phase 1 tasks (approve each task)
       ↓  agent asks: "Phase 1 approved. Raise a draft PR? (Yes / No)"
       ↓  you say Yes → draft PR opened for Phase 1 only
/opsx-e2e my-change --phase 1
       ↓
/opsx-continue   →  tasks for Phase 2 (User Story US-02) … repeat
```

When all phases are done, run **`/opsx-archive`** once for the whole change.

### Starting from an Epic with no Stories in Jira yet

This is the most common first-time setup: you paste a Jira **Epic** key at `/opsx-new`
and the Epic has **no child Stories** yet.

OpenSpec **does not require** Stories to exist upfront. As each phase is planned:

1. **`plan.md`** defines user stories as **US-01**, **US-02**, … (one per phase).
2. After you **approve** that phase's **`tasks.md`**, the agent prompts:
   > *"Phase {N} tasks approved. Create Jira Story [US-XX] \<user story title\> under {Epic-key}? (Yes / No)"*
3. If you answer **Yes** (Jira MCP + credentials required), it creates a **Story** linked
   to your Epic, with summary like `[US-01] Add CRD validation webhooks`.
4. That Story key is stored in `inputs/jira.yaml` → `plan_phases[]` and used as the
   **PR title** when you raise the phase PR in `/opsx-apply`.

You can answer **No** — work continues, but the phase PR title falls back to the Epic
key. Story creation is **optional** but recommended for traceability.

**If your input is already a Story, Task, or Bug** (not an Epic), this prompt is
**skipped** — all work stays on that single ticket.

---

## Step 3 — Configure Jira and GitHub MCP in Cursor

OpenSpec commands use MCP servers so the agent can read Jira tickets, create
Stories, and open GitHub PRs without you copying data by hand.

### Jira MCP

1. Open **Cursor Settings → MCP** (or your team's MCP config).
2. Enable the **Jira** MCP server (`user-jira` or equivalent).
3. Point it at the same Jira host as `credentials.jira.base_url`.
4. Use the same PAT/API token you put in `config.yaml → credentials.jira.api_token`.

Used by: `/opsx-new` (fetch ticket), `/opsx-continue` (create Stories under Epics),
throughout the workflow for ticket metadata.

### GitHub MCP

1. Enable the **GitHub** MCP server (`user-github` or equivalent).
2. Authenticate with a PAT that can read repos, push branches, and open PRs.

Used by: `/opsx-apply` (draft PRs), `/opsx-e2e` (read PR diff and CI).

**If MCP is unavailable:** `/opsx-new` can still run — paste ticket text into
`openspec/changes/<name>/inputs/jira-spec.md` manually when prompted.

---

## Step 4 — One-time operator setup

Run these once per operator repo (or when docs change):

```
/opsx-constitute
```

Generates `harness-evals/constitution.md` from `harness-evals/harness-docs/`.

Create **`agents.md`** at the repo root with your team's coding and test conventions.

For E2E (optional but recommended):

```bash
mkdir -p qe-e2e
cp openspec/openspec/schemas/openspec-agile-workflow/e2e-workflow/qe-behaviour.md qe-e2e/qe-behaviour.md
# Edit Sections 3a and 3b with your operator's namespace, CR kinds, quality gates
```

---

## Step 5 — Start a change (`/opsx-new`)

```
/opsx-new CM-830
/opsx-new CM-830 my-feature-name
/opsx-new CM-830 my-feature-name https://github.com/org/target-repo
/opsx-new https://issues.redhat.com/browse/CM-830
```

### What happens

1. Agent shows the Red Hat AI disclosure notice.
2. Creates `openspec/changes/<name>/` with `inputs/jira.yaml` and `inputs/jira-spec.md`.
3. Fetches the Jira ticket via Jira MCP (or asks you to paste content).
4. **Asks for target repo URL** if you did not pass it inline.
5. Stops — **no planning artifacts yet**.

### Where repo URLs are stored

| URL | When collected | Stored in |
|---|---|---|
| **Target repo** (upstream code you assess/implement against) | `/opsx-new` | `openspec/changes/<name>/inputs/jira.yaml` → `target_repo` |
| **Fork repo** (your fork for code + draft PR) | `/opsx-apply` (or set early in `config.yaml`) | `credentials.github.fork_repo_url` and/or `inputs/jira.yaml` |

You can also pre-fill both in `openspec/config.yaml → credentials.github`:

```yaml
credentials:
  github:
    upstream_repo_url: "https://github.com/openshift/my-operator"
    fork_repo_url: "https://github.com/you/my-operator-fork"
```

**Working-folder mode:** if your Cursor workspace *is* the operator repo, say
**"use this as the working directory"** when asked — no fork URL needed.

### Jira ticket type — when Stories are created

| Input ticket type | Jira Story prompts? |
|---|---|
| **Epic** + `task_execution_mode: phase-iterative` | **Yes — after each phase's `tasks.md` is approved.** The agent asks: *"Create Jira Story [US-XX] \<title\> under {Epic-key}? (Yes / No)"*. Use this when your Epic has **no Stories yet** — OpenSpec creates one Story per phase/user story. Requires Jira credentials + MCP. |
| **Epic** + `task_execution_mode: one-shot` | **Yes** — one Story for the whole change after `plan.md` is approved. |
| **Story**, **Task**, **Bug**, or anything else | **No** — Story creation is skipped; work stays on the original ticket. |

See [How phase-iterative mode works](#how-phase-iterative-mode-works-read-this-on-your-first-run) for the full per-phase loop.

---

## Step 6 — Planning pipeline (`/opsx-continue`)

Run repeatedly until all planning artifacts are approved:

```
/opsx-continue
```

Each run creates **one** artifact, runs the eval gate, and waits for your approval
(when `auto_approve: false`):

| Order | Artifact | Output file |
|---|---|---|
| 1 | Validation | `validation.json` |
| 2 | Specs | `specs.md` |
| 3 | Repo assessment | `repo-assessment.md` |
| 4 | Plan | `plan.md` |
| 5 | Tasks (**one phase at a time** in phase-iterative mode — maps to User Story US-01, US-02, …) | `tasks.md` |

**Approve** to continue to the next artifact. **Reject** with feedback — the agent
refines (except `specs.md` rejection, which exits the workflow per schema rules).

When `tasks.md` for the current phase is approved:

- **Epic input:** you are prompted to create a Jira Story for that phase (see
  [Epic with no Stories](#starting-from-an-epic-with-no-stories-in-jira-yet)).
- Then run **`/opsx-apply`** for that phase — not another `/opsx-continue` unless
  more phases still need task generation.

---

## Step 7 — Implementation (`/opsx-apply`)

```
/opsx-apply
/opsx-apply my-change-name
```

Implements **one phase** (one user story) at a time in phase-iterative mode.

### What happens

1. Reads `tasks.md` for the **current phase** and implements **one task at a time**.
2. After each task: shows a summary and waits for your approval (`auto_approve: false`).
3. Writes per-task reports under `openspec/changes/<name>/task-reports/`.
4. When all tasks in the phase are `[x]`:
   - Writes `implementation-report.md` and optionally `deviation-observed.md`
   - Asks you to **approve the phase implementation**
5. **PR prompt (every phase, never automatic):** after phase approval, the agent asks:
   > *"Phase {N} approved. Would you like to raise a draft PR to the upstream repo?
   > (Yes / No, continue to Phase {N+1})"*
   - **Yes** → opens a **draft PR scoped to this phase only** (fork → upstream)
   - **No** → skip PR and continue to the next phase's planning

Each phase gets its **own PR** (when you say Yes). That is why E2E runs **per phase**
with `/opsx-e2e my-change --phase N` — Phase 1 E2E targets the Phase 1 PR, Phase 2
E2E targets the Phase 2 PR, and so on.

### Fork URL

If `fork_repo_url` is not set, the agent asks before cloning. Provide your fork URL
or use working-folder mode.

After the phase PR is raised (or skipped), you can run **`/opsx-e2e my-change --phase N`**
for that phase — or run E2E later via standalone mode (see Step 8).

---

## Step 8 — E2E tests (`/opsx-e2e`)

`/opsx-e2e` is **decoupled** from planning and implementation. Use it in either scenario:

| Scenario | When | How to invoke |
|---|---|---|
| **After OpenSpec development** | You completed `/opsx-apply` for a phase and have that phase's PR | `/opsx-e2e my-change-name --phase N` (one run per user story/phase) |
| **Standalone** | You have a PR and/or ADR/EP but did **not** run the full OpenSpec workflow | `/opsx-e2e --pr <URL>` and/or `--adr <path>` / `--ep <path>` |

Standalone mode does **not** require `/opsx-new`, `/opsx-continue`, or `/opsx-apply`. Provide at least one of `--pr`, `--adr`, or `--ep`. The agent creates `openspec/changes/<name>/` for E2E artifacts (name derived from the PR, ADR title, or an optional change name).

### Examples

**After OpenSpec development (per phase):**

In **phase-iterative** mode, run E2E **once per phase** after that phase's PR is raised.
Each `--phase N` matches **User Story US-0N** and that phase's PR:

```
/opsx-e2e my-change-name --phase 1    # E2E for Phase 1 / US-01 / Phase 1 PR
/opsx-e2e my-change-name --phase 2    # E2E for Phase 2 / US-02 / Phase 2 PR
```

For **one-shot** mode (all phases in one PR), omit `--phase`:

```
/opsx-e2e my-change-name
```

**Standalone:**

```
/opsx-e2e --pr https://github.com/org/repo/pull/42
/opsx-e2e --adr path/to/adr.md              # design-only mode (no PR yet)
/opsx-e2e --pr <URL> --adr path/to/adr.md   # combined: PR + design context
/opsx-e2e --ep path/to/enhancement-proposal.md
```

### What it does (5 stages)

| Stage | What | Your action |
|---|---|---|
| 1 Pre-analysis | Reads PR/design + operator context; writes impact analysis | **Approve** / reject |
| 2 Test plan | Full test steps + traceability matrix | **Approve** / reject |
| 3 Consolidation | Merges into fewer E2E journeys (respects `qe.max_test_cases`) | **Approve** / reject |
| 4 Code generation | Writes `*_test.go` files | **Approve** / reject |
| 5 Execute & push | Optional local `make test-e2e`; push tests to PR branch | Push / feedback / stop |

### Artifacts created

All under `openspec/changes/<name>/`:

```
e2e/
  e2e-analysis.md           # Stage 1 — impact analysis + operator context
  test-plan.md                # Stage 2 — detailed test plan
  revised-test-plan.md        # Stage 3 — consolidated journeys
  generated/                  # Stage 4 — *_test.go files
  e2e-evaluation-report.md    # Stage 5 — failure analysis (if tests failed)
  e2e-summary.md              # Final summary

telemetry/
  e2e-events.jsonl            # QE lifecycle events
  qe-metrics.json             # QE metrics (coverage, pass rate, cost, …)
```

**Design mode** (ADR/EP only, no PR): stops after Stage 4 — no execute/push until
you re-run with `--pr <URL>`.

**Feedback note:** `/opsx-e2e` does **not** ask for time-saved or story points.
That is collected later by `/opsx-archive`.

---

## Step 9 — Archive the change (`/opsx-archive`)

Run when development is complete (and `/opsx-e2e` has run, if applicable).

```
/opsx-archive
/opsx-archive my-change-name
```

### What happens

1. Checks artifact and task completion (warns if incomplete; you can confirm).
2. **Mandatory feedback** (cannot skip — MON-01 compliance):
   - Estimated manual hours (time saved)
   - Satisfaction (1–5)
   - Comments (optional)
   - **Story points delivered** (mandatory)
3. **QE feedback** (only if `/opsx-e2e` ran — detected via `telemetry/e2e-events.jsonl`):
   - QE time saved (%)
   - QE story points (mandatory when E2E ran)
   - QE comments (optional)
4. Moves the change directory to:
   ```
   openspec/changes/archive/YYYY-MM-DD-<change-name>/
   ```

### Files written at archive

| File | Purpose |
|---|---|
| `user-feedback.md` | Your time-saved, satisfaction, story points, comments |
| `telemetry/metrics-report.json` | Development metrics — marked `report_status.complete: true` after feedback |
| `telemetry/qe-metrics.json` | QE metrics — marked complete after QE feedback (if E2E ran) |

---

## Step 10 — Where to find metrics

| Report | Path |
|---|---|
| Development | `openspec/changes/<name>/telemetry/metrics-report.json` |
| QE / E2E | `openspec/changes/<name>/telemetry/qe-metrics.json` |
| Event log (dev) | `openspec/changes/<name>/telemetry/events.jsonl` |
| Event log (QE) | `openspec/changes/<name>/telemetry/e2e-events.jsonl` |

After archive, the same paths live under
`openspec/changes/archive/YYYY-MM-DD-<name>/telemetry/`.

Key fields in `metrics-report.json`:

- `global_health.total_tokens_consumed` / `estimated_cost_usd`
- `productivity_metrics.story_points_delivered` / `time_saved_hours`
- `report_status.complete` — `true` only after `/opsx-archive` feedback

---

## End-to-end flow (phase-iterative, direct mode)

Each **phase = one user story**. You repeat this block for Phase 1, 2, 3, …

```
Install (install.sh)
    ↓
Configure config.yaml + MCP + credentials
    ↓
/opsx-constitute  (once)
    ↓
/opsx-new <EPIC-KEY> [target-repo-url]     ← Epic with no Stories yet is OK
    ↓
/opsx-continue  →  validation → specs → repo-assessment → plan → tasks (Phase 1 / US-01)
    ↓  approve tasks.md
    ↓  [Epic] "Create Jira Story [US-01] …?"  (Yes / No)
/opsx-apply     →  implement Phase 1 tasks (approve each task)
    ↓  approve phase
    ↓  "Raise draft PR for Phase 1?"  (Yes / No)  ← prompted every phase, never automatic
/opsx-e2e my-change --phase 1              ← E2E for Phase 1 PR / user story
    ↓
/opsx-continue  →  tasks for Phase 2 (US-02) … repeat apply → PR prompt → e2e --phase 2
    ↓
/opsx-archive   →  feedback + move to archive/  (once, after all phases)
```

**Standalone E2E** (no Jira ticket or OpenSpec planning): install OpenSpec, run
`/opsx-constitute` once if needed, then `/opsx-e2e --pr <URL>` and/or `--adr` / `--ep`.

---

## Command cheat sheet

| Command | When to run |
|---|---|
| `/opsx-constitute` | Once — generate constitution |
| `/opsx-new <JIRA>` | Start a new change |
| `/opsx-continue` | Create next planning artifact |
| `/opsx-apply` | Implement current phase (one user story); PR prompt after each phase |
| `/opsx-e2e` | Per phase: `--phase N` after that phase's PR; or standalone with `--pr` / `--adr` |
| `/opsx-archive` | When done — mandatory feedback + archive |
| `/opsx-explore` | Brainstorm without creating artifacts |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Slash commands not found | Restart Cursor after `install.sh` |
| Jira ticket not fetched | Check Jira MCP + `credentials.jira` in `config.yaml` |
| "target_repo not set" | Provide URL at `/opsx-new` or edit `inputs/jira.yaml` |
| "fork_repo_url not set" | Provide at `/opsx-apply`, or use working-folder mode |
| No Jira Story created | Input must be an **Epic**; Story/Task/Bug skips Story creation |
| Story creation skipped | Fill `credentials.jira.base_url` and `api_token` |
| `/opsx-e2e` blocked | Ensure `agents.md` + `harness-evals/constitution.md` exist |
| Metrics incomplete at archive | Answer all mandatory questions (story points required) |

For full reference material, see [README.md](../README.md).
