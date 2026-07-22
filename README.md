# openspec-agile-workflow

Custom [OpenSpec](https://github.com/Fission-AI/OpenSpec) schema for **gated, Jira-driven, spec-first development** with AI-assisted planning and implementation. Supports two code-generation strategies: **ai-helpers** (OAPE command routing + eval gate) and **direct** (plain agent implementation).

---

## Quick Start

### 1. Clone & Install

```bash
rm -rf /tmp/openspec-workflow
git clone -b containerization https://github.com/sujkini/openspec.git /tmp/openspec-workflow
/tmp/openspec-workflow/install.sh /path/to/your-operator-repo
```

This copies `openspec/`, `.cursor/`, `.devcontainer/`, `eval-generation/`, and `dashboard/` into your project, installs the OpenSpec CLI, and sets up dependencies. Use `--no-dashboard` to skip the dashboard.

### 2. (Optional) Open in Dev Container

A `.devcontainer/` configuration is included for running the workspace inside a reproducible container with Python 3.12, Node 20, Go 1.22, git, and gh CLI pre-installed.

1. Copy `.devcontainer/.env.example` to `.devcontainer/.env` and fill in your values:
  ```bash
   cp .devcontainer/.env.example .devcontainer/.env
   # Edit .devcontainer/.env:
   #   OPENSPEC_STATE_REPO=https://github.com/<org>/openspec-state.git
   #   GIT_TOKEN=ghp_...
  ```
2. **Ensure Docker is running** before opening the container:
  ```bash
   docker info    # Should show both Client and Server sections
  ```
   If the Server section is empty or you see `Error running docker info`, start the daemon:
   Verify with `docker info` again — the **Server** section must show `Server Version`, `Storage Driver`, etc.
3. **Ensure your user can run Docker without sudo**:
  ```bash
   # If "docker info" requires sudo, add yourself to the docker group:
   sudo usermod -aG docker $USER
   newgrp docker    # or log out and back in
  ```
4. **Fix file permissions** (if repo files are owned by root):
  ```bash
   # Run on the HOST (outside the container), not inside it
   bash .devcontainer/fix-host-permissions.sh
  ```
   Or manually:
   Skip this step if you already own the files (`ls -la` shows your username, not `root`).
5. **Install the Dev Containers extension** in Cursor (or VS Code):
  - Open Extensions (`Ctrl+Shift+X`)
  - Search for **Dev Containers** (publisher: Microsoft, ID: `ms-vscode-remote.remote-containers`)
  - Install it before reopening the workspace in a container
6. **Connect MCP servers** (GitHub + Jira) — required for `/opsx-new`, state repo creation, and handover notifications.
  Open (or create) `~/.cursor/mcp.json`:
  - **GitHub MCP** — `create_repository`, `get_file_contents` (used by `/opsx-new` for the state repo)
  - **Jira MCP** — `jira_add_comment`, `jira_search_users`, `jira_get_issue` (ticket fetch and handover @mentions)
   Set `JIRA_USERNAME` to your work email — RBAC identity checks compare it to `inputs/rbac.yaml` phase owners.
   Restart Cursor after editing `mcp.json`. Full reference: [Step 5: Connect MCP Servers](#5-connect-mcp-servers-github--jira).
7. In Cursor: `Ctrl+Shift+P` → **"Dev Containers: Reopen in Container"**
8. **Inside the container** — verify environment and set up credentials:
  ```bash
   # Disable git signing (SSH signing keys from host are not available in container)
   git config --global commit.gpgsign false
   git config --global tag.gpgsign false

   # Set state sync credentials
   export OPENSPEC_STATE_REPO=https://github.com/<your-org>/openspec-state.git
   export GIT_TOKEN=ghp_<your-token>

   # Verify tools and modules are installed
   ls openspec/state_sync.py openspec/rbac.py openspec/jira_notify.py
   ls .cursor/commands/opsx-resume.md
   grep state_sync openspec/config.yaml
   pip install -r openspec/telemetry/requirements.txt
   python3 -c "import yaml; print('pyyaml OK')"
  ```
9. **Multi-owner handover (User B and later owners):**
  - Use the **same** `OPENSPEC_STATE_REPO` URL that User A created at `/opsx-new` (from team docs, User A's `.devcontainer/.env`, or `state_repo_url` in `inputs/jira.yaml` on the state branch). Do **not** create a separate state repo.
  - Set in `.devcontainer/.env` or your shell:
    ```bash
    export OPENSPEC_STATE_REPO=https://github.com/<org>/openspec-state.git
    export GIT_TOKEN=ghp_<your-token-with-repo-access>
    ```
  - **User A must grant access** to the shared state repo for every handover recipient (GitHub → repo **Settings → Collaborators**, or org team with repo access). Without this, User B's `/opsx-resume` fails on `git pull`.
  - User B needs their **own** operator repo clone with `install.sh` already run; only the state repo is shared.
  - Ensure `JIRA_USERNAME` in `~/.cursor/mcp.json` matches the email assigned in `inputs/rbac.yaml` for the phase User B is resuming — `/opsx-resume` and `/opsx-continue` enforce this.

The dev container is optional — the workflow works without it. It is recommended when using RBAC multi-owner handover so each owner gets a consistent environment.

#### Dev Container Troubleshooting


| Problem                                                         | Cause                                          | Fix                                                                                                         |
| --------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `Error running docker info` / empty Server section              | Docker daemon not running                      | `sudo systemctl start docker` (Linux) or open Docker Desktop (macOS/Windows)                                |
| `permission denied` on `/var/run/docker.sock`                   | User not in docker group                       | `sudo usermod -aG docker $USER` then re-login                                                               |
| `ls: cannot open directory: Permission denied` inside container | Host files owned by root                       | Run on **host**: `sudo chown -R $USER:$USER /path/to/repo`                                                  |
| `pip install -r ... Permission denied` inside container         | Same root ownership issue                      | Same fix: `chown` on host, then rebuild container                                                           |
| `fatal: failed to write commit object` / GPG signing error      | SSH signing key not in container               | Inside container: `git config --global commit.gpgsign false`                                                |
| SELinux blocking reads (Fedora)                                 | Wrong file context on mount                    | Run on **host**: `sudo chcon -R -t container_file_t /path/to/repo`                                          |
| Podman instead of Docker                                        | Dev Containers extension expects Docker socket | Set in Cursor settings: `"docker.environment": {"DOCKER_HOST": "unix:///run/user/1000/podman/podman.sock"}` |
| `postCreateCommand` failed silently                             | Usually caused by the permission issues above  | Fix permissions, then `Ctrl+Shift+P` → **"Dev Containers: Rebuild Container"**                              |


### 3. Choose code generation mode (`openspec/config.yaml`)

Set `flags.codegen_mode` before you start implementing tasks:

```yaml
# openspec/config.yaml
flags:
  codegen_mode: ai-helpers   # or: direct
```


| Mode                       | When to use                                                                                      | What `/opsx-apply` does                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| `**ai-helpers**` (default) | API/controller/e2e work that benefits from specialized OAPE Cursor commands and a code eval gate | design-bundle → OAPE command → verify → code eval → refine → approve             |
| `**direct**`               | Straightforward tasks; simpler/faster path                                                       | agent reads context → FILE OPERATIONS → verify → approve (no OAPE, no code eval) |


Change the flag anytime; `/opsx-apply` reads it on each invocation. Details below under [Configuration](#configuration-openspecconfigyaml).

### 4. Start the Dashboard

```bash
cd /path/to/your-operator-repo
./dashboard/start.sh
```

Installs deps on first run, starts the FastAPI backend (port 8000) and React frontend (port 5173). Open [http://localhost:5173](http://localhost:5173). The backend polls `openspec/changes/` for telemetry data written by `/opsx-*` commands. See `dashboard/README.md` for details.

### 5. Connect MCP Servers (GitHub + Jira)

The workflow uses two MCP servers for external integrations. Add them to your Cursor MCP config.

Open (or create) your MCP config file at `~/.cursor/mcp.json` and add:

```json
{
  "mcpServers": {
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer <your-github-pat>"
      }
    },
    "jira": {
      "command": "uvx",
      "args": ["mcp-atlassian", "--toolsets", "default,jira_users"],
      "env": {
        "JIRA_URL": "https://redhat.atlassian.net",
        "JIRA_USERNAME": "<your-email>@redhat.com",
        "JIRA_API_TOKEN": "<your-jira-api-token>"
      }
    }
  }
}
```

**GitHub MCP** — provides `create_repository`, `get_file_contents`, and other GitHub API tools. Used by `/opsx-new` to auto-create the state repo. Generate a PAT at [GitHub Settings → Tokens](https://github.com/settings/tokens) with `repo` scope.

**Jira MCP** (`mcp-atlassian`) — provides `jira_add_comment`, `jira_search_users`, `jira_get_issue`. Used for fetching ticket data and posting handover notifications. Generate an API token at [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens). Requires `uvx` (install via `pip install uvx` or `pipx install uv`).

After editing `mcp.json`, restart Cursor so both servers connect.

### 6. Restart Cursor

Restart Cursor so slash commands load from `.cursor/commands/` and MCP servers connect.

### 7. Run your first change

```
/opsx-new PROJ-123
```

---

## Configuration

After installation, configure two files in `openspec/inputs/`:


| File                                  | What to define                                                             |
| ------------------------------------- | -------------------------------------------------------------------------- |
| `**openspec/inputs/agents.md**`       | Agent routing, repository architecture, test patterns, verification matrix |
| `**openspec/inputs/constitution.md**` | Coding guardrails, CI gates, governance rules                              |


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

## RBAC Phase Ownership (Multi-Owner Handover)

When multiple people own different phases of a change, RBAC configuration enables automatic handover with Jira notifications.

### Setup

During `/opsx-new`, you are prompted to assign phase owners:

```
Spec validation owner: alice@redhat.com
Repo assessment owner: bob@redhat.com
Planning owner:        bob@redhat.com
Tasks owner:           alice@redhat.com
Code generation owner: charlie@redhat.com
```

This writes `openspec/changes/<change>/inputs/rbac.yaml`:

```yaml
epic_owner: epic-owner@redhat.com
phase_owners:
  spec_understanding:
    owner: alice@redhat.com
  repo_assessment:
    owner: bob@redhat.com
  arch_planning:
    owner: bob@redhat.com
  subtask_creation:
    owner: alice@redhat.com
  code_generation:
    owner: charlie@redhat.com
```

Skip the prompt (or omit all emails) for single-owner mode — no handover gates activate.

### RBAC module

The `openspec/rbac.py` module provides:

- `load_rbac_config(change_dir)` — load `inputs/rbac.yaml`
- `is_handover_needed(config, current_phase)` — check if owners differ
- `get_phase_owner(config, phase)` / `get_next_phase_owner(config, phase)`
- `validate_rbac_config(config)` — validate emails and phase names
- `resolve_current_user_email()` — identity from `JIRA_USERNAME`, `OPENSPEC_USER_EMAIL`, or git `user.email`
- `verify_user_is_phase_owner(config, phase, user_email)` — enforced by `/opsx-resume`, `/opsx-continue`, and `/opsx-apply`

---

## State Sync (Artifact Persistence)

State sync pushes `openspec/changes/<change>/` artifacts to a **dedicated git repository** after each phase completes. This enables multi-owner handover — each owner pulls the shared state from the same branch.

### Do I need to create the state repo manually?

**No.** The `/opsx-new` command auto-creates the state repo via GitHub MCP if it does not already exist:

1. It reads the `OPENSPEC_STATE_REPO` env var.
2. If the env var is set and the repo exists → uses it directly.
3. If the env var is empty or the repo does not exist → calls GitHub MCP `create_repository` to create a **public** repo named `openspec-state` under your GitHub org.
4. You are informed: `"Created state repo: <url>"`.

If you prefer to create it manually, create an **empty public repo** on GitHub (e.g. `yourorg/openspec-state`) and set the env var before running `/opsx-new`.

### Configuration

In `openspec/config.yaml`:

```yaml
state_sync:
  enabled: true
  repo_env_var: OPENSPEC_STATE_REPO
  token_env_var: GIT_TOKEN
  branch_pattern: "{jira_key}/{change_slug}"
```

Set environment variables (or add to `.devcontainer/.env`):

```bash
export OPENSPEC_STATE_REPO=https://github.com/<org>/openspec-state.git
export GIT_TOKEN=ghp_...
```

### How state sync commits and pushes

State sync is triggered **automatically via telemetry hooks** in `openspec/telemetry/auto.py`. The flow is:

1. User approves an artifact in `/opsx-continue` or a task in `/opsx-apply`.
2. The command calls the telemetry hook (e.g. `on-artifact-complete`, `on-task-complete`).
3. At the end of each telemetry hook, `_try_state_sync()` is called automatically.
4. `_try_state_sync()` calls `openspec/state_sync.py → sync_state()` which:
  - Clones (or reuses a cached clone of) the state repo into `/tmp/openspec-state-cache/`
  - Checks out (or creates) the branch `<JIRA-KEY>/<change-slug>`
  - Copies all files from `openspec/changes/<change>/` into the clone
  - Commits with message `[openspec] <phase_name> complete - <JIRA-KEY>`
  - Pushes to the remote state repo using `GIT_TOKEN` for authentication
5. State sync is **best-effort** — a push failure logs a warning but **never** blocks the workflow.

The four hook points where state sync fires:


| Telemetry hook         | When it fires                                       | What was just completed                  |
| ---------------------- | --------------------------------------------------- | ---------------------------------------- |
| `on-artifact-complete` | After user approves an artifact in `/opsx-continue` | validation.json, specs.md, plan.md, etc. |
| `on-task-complete`     | After user approves a task in `/opsx-apply`         | A single implementation task             |
| `on-phase-complete`    | After all tasks in a plan phase are done            | An entire plan phase (e.g. Phase 1)      |
| `on-apply-complete`    | After all phases and tasks are done                 | The entire implementation                |


---

## Jira Notifications

When RBAC is configured, Jira comments are posted automatically on the child ticket at phase boundaries. The Jira MCP server must be connected in `~/.cursor/mcp.json` (see [Step 5: Connect MCP Servers](#5-connect-mcp-servers-github--jira)).


| Event                                 | Who is notified               | Comment content                                   |
| ------------------------------------- | ----------------------------- | ------------------------------------------------- |
| Phase complete (same owner continues) | Current owner (informational) | Phase name, status, quality score                 |
| Phase complete (handover needed)      | Next owner (`@mentioned`)     | Handover instructions with `/opsx-resume` command |
| All phases complete                   | Epic owner                    | Summary of all phases with state repo link        |
| Phase failed                          | Phase owner + Epic owner      | Error summary                                     |


Mentions use Jira Cloud `[~accountid:<id>]` format. Account IDs are resolved via Jira MCP `jira_search_users` on first use and cached in `inputs/rbac.yaml`.

The `openspec/jira_notify.py` module formats comment text. The actual Jira API call is made by the Cursor agent via the Jira MCP `jira_add_comment` tool.

---

## End-to-End Handover Flow (Owner A → Owner B)

This is the complete step-by-step lifecycle when phases have different owners.

### Owner A starts the change

1. **Owner A** opens their operator repo clone in Cursor (optionally in the dev container).
2. Owner A runs:
  ```
   /opsx-new OAPE-850
  ```
3. `/opsx-new` fetches the Jira ticket, auto-creates the state repo (if needed), and prompts for RBAC:
  ```
   Spec validation owner: alice@redhat.com     ← Owner A
   Repo assessment owner: bob@redhat.com       ← Owner B
   ...
  ```
4. Owner A runs `/opsx-continue` repeatedly to generate and approve artifacts (`validation.json`, `specs.md`).
5. After `specs.md` is approved, the telemetry hook fires → **state sync pushes** all artifacts to branch `OAPE-850/oape-850` in the state repo.
6. `/opsx-continue` detects that the **next phase (repo_assessment) has a different owner** ([bob@redhat.com](mailto:bob@redhat.com)):
  - Posts a **Jira comment** on OAPE-850 with `@bob` mention:
  - Outputs to Owner A:
    ```
    ═══════════════════════════════════════════════
    HANDOVER: spec_understanding is complete.
    Next phase (repo_assessment) is assigned to bob@redhat.com.
    A Jira notification has been posted on OAPE-850.
    The assigned owner must run /opsx-resume OAPE-850 then /opsx-continue.
    ═══════════════════════════════════════════════
    ```
  - **HARD STOP** — Owner A cannot proceed further. The command refuses to generate the next artifact.

### Owner B picks up the change

1. **Owner B** gets the Jira notification (email or watched ticket).
2. Owner B opens **their own** operator repo clone in Cursor (their own workspace, not Owner A's).
3. Owner B must have:
  - `install.sh` already run on their repo (so `openspec/`, `.cursor/`, `.devcontainer/` are present)
  - The **same** `OPENSPEC_STATE_REPO` URL as User A (not a new repo) and a `GIT_TOKEN` with push access to that repo
  - **Collaborator access** to the state repo granted by User A (or an org admin)
  - Jira MCP connected in `~/.cursor/mcp.json` with `JIRA_USERNAME` matching their assigned email in `inputs/rbac.yaml`
4. Owner B runs:
  ```
    /opsx-resume OAPE-850
  ```
    This:
  - Finds branch `OAPE-850/oape-850` in the state repo
  - Pulls all artifacts into `openspec/changes/oape-850/` locally
  - Verifies the state is valid
  - Shows:
    ```
    ═══════════════════════════════════════════════
    RESUMED: oape-850
    Jira: OAPE-850
    State branch: OAPE-850/oape-850
    Last completed phase: spec_understanding (by alice@redhat.com)
    Next phase: repo_assessment (assigned to you)
    ═══════════════════════════════════════════════

    Run /opsx-continue to start the next phase.
    ```
5. Owner B runs `/opsx-continue` to generate `repo-assessment.md`, approve it, and continue.
6. If Owner B also owns the next phase (e.g. `arch_planning`), they keep running `/opsx-continue` — no handover.
7. When the next phase has a **different owner** again, the handover cycle repeats (steps 5–11).

### Key points

- Each owner works in **their own Cursor IDE** with their own clone of the operator repo.
- `/opsx-resume` is the bridge — it pulls the shared state into the new owner's workspace.
- The state repo branch is the **single source of truth** that travels between owners.
- If the same owner handles consecutive phases, no handover happens — they just keep running `/opsx-continue`.
- The handover is a **hard stop** — the current owner cannot override it.
- **Identity checks** — `/opsx-resume`, `/opsx-continue`, and `/opsx-apply` compare `JIRA_USERNAME` (or git `user.email`) to the email in `inputs/rbac.yaml` and refuse if they do not match.

---

## Cursor Commands

### Forward workflow


| Command                 | Purpose                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `/opsx-new PROJ-123`    | Start a change from a Jira key; optionally configure RBAC + state repo             |
| `/opsx-continue`        | Create next artifact; eval gate; approval; handover check                          |
| `/opsx-apply`           | Implement tasks — one at a time, approval after each; handover at phase boundaries |
| `/opsx-resume PROJ-123` | Pull state from the state repo for multi-owner handover                            |
| `/opsx-archive`         | Archive a completed change                                                         |
| `/opsx-explore`         | Explore ideas without creating artifacts                                           |


### OAPE commands (ai-helpers mode only, during `/opsx-apply`)


| Command                    | When                          |
| -------------------------- | ----------------------------- |
| `/oape:api-generate`       | API_Agent task                |
| `/oape:api-generate-tests` | API_Agent verification task   |
| `/oape:api-implement`      | OperatorController_Agent task |
| `/oape:e2e-generate`       | E2E / Testing_Agent task      |


These commands are **not used** when `codegen_mode: direct`.

### Retrospective eval loop


| Command      | Purpose                                       |
| ------------ | --------------------------------------------- |
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


| Flag                         | Default      | What it does                                                                                                             |
| ---------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `codegen_mode`               | `ai-helpers` | Code generation strategy: `ai-helpers` (OAPE commands + code eval gate) or `direct` (plain agent, no OAPE, no eval gate) |
| `max_feedback_rounds`        | 3            | Max rejection + refinement loops per artifact before halting                                                             |
| `exit_on_all_tasks_complete` | true         | Auto-exit implementation when all tasks marked `[x]`                                                                     |


### Code generation modes

`**ai-helpers**` — For each task, composes a `design-bundle.md`, routes to specialized OAPE Cursor commands (`api-generate`, `api-implement`, `e2e-generate`), scores generated code via a code-generation eval gate, refines until evals pass, then asks for user approval.

`**direct**` — The Cursor agent reads context files directly, implements code via FILE OPERATIONS, verifies against acceptance criteria, and asks for user approval. No OAPE commands, no design bundles, no code eval gate. Simpler and faster for straightforward tasks.

---

## Eval Loop (Optional, Recommended)

The eval loop is a **retrospective improvement** tool. After a feature is fully completed, feed its history into `/eval-loop` to generate eval cases that improve the quality of future runs.

### Step 1: Provide inputs

Fill `eval-generation/input/feature-bundle.yaml` with data from a **completed feature**:


| Field                  | What to paste                   |
| ---------------------- | ------------------------------- |
| `feature_name`         | Feature name                    |
| `epic_key`             | Jira epic key                   |
| `target_repo`          | Target repository URL           |
| `enhancement_proposal` | Full EP/ARD content             |
| `jira_epic`            | Jira epic export                |
| `repo_state`           | Pre-feature repo state          |
| `user_stories`         | User stories linked to the epic |
| `repo_prs`             | PR links and key diffs          |
| `bugs`                 | Bug list with root causes       |


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


| Stage                    | Artifacts                         | Purpose                                                                   |
| ------------------------ | --------------------------------- | ------------------------------------------------------------------------- |
| **Spec understanding**   | `validation.json`, `specs.md`     | Validate Jira spec before repo work                                       |
| **Repo understanding**   | `repo-assessment.md`              | Ground planning in the target repository                                  |
| **Constitution (input)** | `constitution.md` (resolved)      | Non-negotiable guardrails                                                 |
| **Planning**             | `plan.md`                         | Phased implementation plan                                                |
| **Task creation**        | `tasks.md`                        | Executable task manifest with agents                                      |
| **Implementation**       | code + `implementation-report.md` | Task-by-task execution with per-task approval (ai-helpers or direct mode) |
| **Archive**              | archived change                   | Close out                                                                 |


---

## Prerequisites

### Required


| Requirement                                            | Notes                                                      |
| ------------------------------------------------------ | ---------------------------------------------------------- |
| [Node.js](https://nodejs.org/) 18+                     | For OpenSpec CLI installation                              |
| [Python](https://python.org/) 3.12+                    | For telemetry, state sync, RBAC modules                    |
| [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) | Installed automatically by `install.sh`                    |
| [Cursor](https://cursor.com)                           | Slash commands load from `.cursor/commands/`               |
| Jira access                                            | Ticket key at `/opsx-new`; spec via Jira MCP or paste      |
| Target GitHub repo                                     | URL before **repo-assessment**; or use working-folder mode |
| Fork GitHub repo                                       | URL before `/opsx-apply`; skip in working-folder mode      |


### Required for RBAC / Jira notifications


| Requirement                                                                       | Notes                                                                                                       |
| --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [Atlassian MCP](https://www.npmjs.com/package/@anthropic/atlassian-mcp) in Cursor | Authenticate via Cursor Settings → MCP → `user-atlassian`. Provides `jira_add_comment`, `jira_search_users` |
| GitHub PAT (`GIT_TOKEN`)                                                          | Token with `repo` scope for pushing to the state repo                                                       |
| State repo (`OPENSPEC_STATE_REPO`)                                                | Dedicated public repo for artifact persistence (auto-created by `/opsx-new` if missing)                     |


### Required for dev container


| Requirement                                                                                                                   | Notes                                                                                                                                                                             |
| ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman](https://podman.io/)                             | Container runtime for building and running the dev container                                                                                                                      |
| [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for Cursor | Install from Extensions panel — search "Dev Containers" by Microsoft (`ms-vscode-remote.remote-containers`). Required to use `Ctrl+Shift+P → Dev Containers: Reopen in Container` |


---

## Repository Layout

```
.
├── openspec/                              # Pre-built — ready to use after install
│   ├── config.yaml                        # Workflow configuration, flags, state_sync settings
│   ├── state_sync.py                      # Git-based state sync for multi-owner handover
│   ├── rbac.py                            # RBAC phase-owner mapping and handover logic
│   ├── jira_notify.py                     # Jira comment templates for notifications
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
├── .devcontainer/                         # Dev container for reproducible environments
│   ├── devcontainer.json                  # Container config (Python, Node, Go, git, gh)
│   ├── Containerfile                      # Base image definition
│   └── .env.example                       # Template for OPENSPEC_STATE_REPO, GIT_TOKEN
├── .cursor/                               # Pre-built — Cursor loads immediately
│   ├── commands/                          # opsx-new, opsx-continue, opsx-apply, opsx-resume, eval-loop
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