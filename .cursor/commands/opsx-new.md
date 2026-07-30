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
| **Jira ticket key or URL** | **YES** | — | Always the first input |
| **Target GitHub repo URL** | **YES** | — | Asked during `/opsx-new` if not provided inline |
| **Fork GitHub repo URL** | No | **YES** | Before `/opsx-apply` (skip in working-folder mode) |
| **Change name** (kebab-case) | No | — | Optional; defaults to lowercase ticket slug (`PROJ-123` → `proj-123`) |
| **AGENTS.md** | No | No | Optional |

## Command syntax

```
/opsx-new CM-830
/opsx-new CM-830 my-change-name
/opsx-new CM-830 my-change-name https://github.com/org/repo
/opsx-new https://issues.redhat.com/browse/CM-830
/opsx-new https://issues.redhat.com/browse/CM-830 https://github.com/org/repo
```

Jira key pattern: `[A-Z][A-Z0-9]+-\d+`.
Jira URL pattern: `https://<host>/browse/<KEY>` — extract the key from the URL.

If no Jira key or URL, ask once. Do **not** proceed without it.

## Steps

1. Parse Jira key or URL (required), optional change name, optional repo URL.
   - If a Jira URL is provided (e.g. `https://issues.redhat.com/browse/CM-830`), extract the key from the path.
2. **Ask for target repo URL** (if not provided inline):
   ASK: **"What is the target GitHub repository URL? (e.g. https://github.com/org/repo)"**
   - Store in `inputs/jira.yaml` → `target_repo`
   - This is needed for repo-assessment and implementation stages
3. `openspec new change "<name>"` — uses `openspec-agile-workflow` from `openspec/config.yaml`.
4. Write `openspec/changes/<name>/inputs/jira.yaml` with `jira_key`, `jira_url`, `target_repo`, `created_at`.
5. **Fetch ticket + epic metadata** → `inputs/jira-spec.md` + enrich `inputs/jira.yaml`:
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
6. **Telemetry — register run** (silent, non-blocking):
   ```bash
   python -m openspec.telemetry.auto on-new --change "<name>" --jira-key "<JIRA-KEY>"
   ```
7. `openspec status --change "<name>"` and `openspec instructions validation --change "<name>"`.
8. **STOP** — do not create artifacts yet.

Prompt: `/opsx-continue` to create `validation.json`.

## Guardrails

- Jira key or URL required; extract key from URL if URL provided
- Target repo URL required — ask if not provided inline
- No planning artifacts in this command
