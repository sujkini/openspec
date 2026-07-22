---
name: /opsx-new
id: opsx-new
category: Workflow
description: Start a new agile-workflow change from a Jira ticket (OPSX)
---

Start a new change for the **openspec-agile-workflow** pipeline.

## Inputs — what is required when

| Input | Required at `/opsx-new`? | Required later? | When |
|-------|--------------------------|-----------------|------|
| **Jira ticket key** | **YES** | — | Always the first input |
| **Change name** (kebab-case) | No | — | Optional; defaults to lowercase ticket slug (`PROJ-123` → `proj-123`) |
| **Target GitHub repo URL** | **NO** | **YES** | Before **repo-assessment** (`/opsx-continue` ~3rd artifact) |
| **AGENTS.md** | No | No | Optional |

**At `/opsx-new` you only need the Jira key.** Do not ask for the repo URL unless the user includes it inline.

## Command syntax

```
/opsx-new CM-830
/opsx-new CM-830 my-change-name
/opsx-new CM-830 my-change-name https://github.com/org/repo
```

Jira key pattern: `[A-Z][A-Z0-9]+-\d+`.

If no Jira key, ask once. Do **not** proceed without it.

## Steps

1. Parse Jira key (required), optional change name, optional repo URL.
2. `openspec new change "<name>"` — uses `openspec-agile-workflow` from `openspec/config.yaml`.
3. Write `openspec/changes/<name>/inputs/jira.yaml` with `jira_key`, `target_repo`, `created_at`.
4. **Fetch ticket + epic metadata** → `inputs/jira-spec.md` + enrich `inputs/jira.yaml`:
   - Use Jira MCP `jira_get_issue` with `issue_key: "<JIRA-KEY>"` and
     `fields: "summary,status,issuetype,parent,customfield_10014"`.
   - From the response, extract and persist to `inputs/jira.yaml`:
     - `jira_summary`: issue summary field
     - `jira_url`: `https://issues.redhat.com/browse/<JIRA-KEY>`
     - `epic_key`: from `parent.key` or `customfield_10014` (epic link) when present
     - `epic_name`: from `parent.fields.summary` or a follow-up `jira_get_issue` on the epic key
     - `epic_url`: `https://issues.redhat.com/browse/<epic_key>` when epic_key exists
     - `jira_fetched_at`: current ISO8601 timestamp
   - Write ticket description + acceptance criteria to `inputs/jira-spec.md`.
   - If Jira MCP is unavailable, ask the user to paste ticket content into `inputs/jira-spec.md`
     and manually provide epic info if known (optional).
   - **Note:** Spec-understanding phase telemetry does NOT start here — it begins at
     `/opsx-continue` step 6 (`on-artifact-start --artifact validation`). `/opsx-new` only
     registers the run.
4a. **State repo setup** (if `openspec/config.yaml` → `state_sync.enabled` is true):
   - Read `OPENSPEC_STATE_REPO` env var.
   - If the env var is set, verify the repo is accessible (silent check via GitHub MCP
     `get_file_contents` on `README.md`, or `git ls-remote`). If accessible, persist
     `state_repo_url` to `inputs/jira.yaml`.
   - If the env var is empty or the repo does not exist:
     - If `target_repo` was provided, derive the GitHub org from its URL.
       Otherwise ask the user once: "GitHub org for the state repo? (e.g. `myorg`)"
     - Call GitHub MCP `create_repository` with `name: "openspec-state"`, `org: "<org>"`,
       `private: false`, `description: "OpenSpec workflow state artifacts"`.
     - Persist the new repo URL to `inputs/jira.yaml` as `state_repo_url`.
     - Inform user: "Created state repo: `<url>`"
   - Create the initial branch `<jira-key>/<change-slug>` with an initial commit
     containing `inputs/jira.yaml`:
     ```bash
     python -c "from openspec.state_sync import sync_state; sync_state('<name>', 'init', '<JIRA-KEY>')"
     ```

4b. **RBAC configuration** (optional):
   - ASK the user:
     ```
     Define phase owners for this change? Enter email addresses per phase, or "skip" to use single-owner mode (no handover).

     Spec validation owner: [email or skip]
     Repo assessment owner: [email or skip]
     Planning owner:        [email or skip]
     Tasks owner:           [email or skip]
     Code generation owner: [email or skip]
     ```
   - If the user provides at least one email: write `inputs/rbac.yaml` with the
     phase-owner mapping. Use the `openspec.rbac` module to validate and persist:
     ```yaml
     epic_owner: <epic_owner_email_if_known>
     phase_owners:
       spec_understanding:
         owner: <email>
       repo_assessment:
         owner: <email>
       ...
     ```
     Validate emails with `openspec.rbac.validate_rbac_config()`.
   - If all skipped or user says "skip": do not create `rbac.yaml`. Single-owner
     mode — no handover gates will activate.

5. **Telemetry — register run** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-new --change "<name>" --jira-key "<JIRA-KEY>"
   ```
6. `openspec status --change "<name>"` and `openspec instructions validation --change "<name>"`.
7. **STOP** — do not create artifacts yet.

Prompt: `/opsx-continue` to create `validation.json`.

## Guardrails

- Jira key required; repo URL optional at this step
- No planning artifacts in this command
- State repo auto-creation requires GitHub MCP (`create_repository` permission)
- RBAC is optional — omitting it disables the handover flow entirely
