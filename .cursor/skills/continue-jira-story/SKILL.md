# Jira Story Creation

Create Jira Story tickets after artifact approval. Called by `continue-artifact` skill post-approval.

## Trigger Conditions

**Step 11b — One-shot mode:**
- Artifact is `plan` AND `task_execution_mode = one-shot` AND status passed
- Creates a single Story representing the entire implementation work

**Step 12 — Phase-iterative mode:**
- Artifact is `tasks` AND `task_execution_mode = phase-iterative` AND status passed
- Creates one Story per phase, mapped to the phase's user story

## Steps

### 1. Check Prerequisites

- Read `inputs/jira.yaml` → `jira_issuetype`.
- **If `jira_issuetype` != "Epic":** skip Story creation entirely. Output "Input ticket is a {jira_issuetype}, not an Epic. Jira Story creation skipped." Return.
- Read `config.yaml → credentials.jira` for `base_url` and `api_token`.
- **If credentials empty:** skip with message. Write `plan_phases[]` entry with `jira_key: SKIPPED (no credentials)`. Return.

### 2. Auto-Approve Check

Read `config.yaml → flags.auto_approve`.

- **If `auto_approve: true`:** auto-create Story (skip prompt). Proceed.
- **If `auto_approve: false`:**
  - **One-shot:** ASK "Plan approved. Create a Jira Story for this change under {jira_key}? (Yes / No)"
  - **Phase-iterative:** ASK "Phase {N} tasks approved. Create Jira Story [US-XX] <user story title> under {jira_key}? (Yes / No)"

On **No**: write `plan_phases[]` entry with `jira_key: SKIPPED`. Return.

### 3. Create Story via Jira MCP

Call Jira MCP `create_ticket`:
- `project`: prefix of parent key (e.g. `CM` from `CM-800`)
- `issuetype`: `Story`
- `parent`: `jira_key` (the Epic)
- `summary`:
  - One-shot: `<change-name>: <plan title> (US-01, US-02, ...)`
  - Phase-iterative: `[US-XX] <user story title>`
- `description`: Developer-style ticket with:
  - User story acceptance criteria from specs.md
  - Phase goal, target files from plan.md
  - OpenSpec change path reference
  - Parent Epic reference
  - AI disclaimer

### 4. Persist

Write to `inputs/jira.yaml` → `plan_phases[]`:
```yaml
plan_phases:
  - phase: <N|all>
    jira_key: <created-key>
    jira_url: <browse-url>
    summary: "<summary>"
    issuetype: Story
    parent: <jira_key>
```

If Jira MCP unavailable: set `jira_key: PENDING`. Do NOT block the workflow.

Report created / PENDING / SKIPPED key in the approval summary.
