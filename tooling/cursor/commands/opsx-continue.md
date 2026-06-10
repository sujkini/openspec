---
name: /opsx-continue
id: opsx-continue
category: Workflow
description: Continue agile-workflow change - create next artifact (OPSX)
---

Continue working on a change by creating the **next** artifact (one per invocation).

**Input**: Optional change name after `/opsx-continue` (e.g. `/opsx-continue cm-830`).

## Steps

1. Select change (`openspec list --json` if name not given).
2. `openspec status --change "<name>" --json`
3. **Agile workflow**: Read `openspec/changes/<name>/inputs/jira.yaml` (required). Use `jira_key` for validation/specs; `target_repo` for repo-assessment (ask if empty).
4. Pick first artifact with `status: "ready"`.
5. `openspec instructions <artifact-id> --change "<name>" --json` → create artifact at `outputPath`.
6. **STOP** after one artifact. Ask: "Approve / Reject with feedback?" before next continue.

## Artifact order (openspec-agile-workflow)

validation.json → specs.md → repo-assessment.md → constitution.md → plan.md → tasks.md

## Guardrails

- ONE artifact per invocation
- Do not skip gates
- Repo URL required before repo-assessment (not at `/opsx-new`)
