# Code Generation Eval Gate — Forward workflow (`/opsx-apply` per task)

Score **generated or modified code** in the fork working copy after each task's OAPE command (or manual agent work), **refine code until evals pass**, then present for **user code approval**.

Paths below are **relative to the schema root** (`openspec/schemas/openspec-agile-workflow/` when installed).

## Mandatory per-task sequence

**Do not skip steps. Do not ask for user approval before completing the eval refinement loop.**

```
1. Execute OAPE command (or manual agent work) in fork cwd
2. Verify task Acceptance criteria (make targets)
3. Run code-generation evals (filter by oape_command)
4. IF any case fails → fix code in fork → re-verify → re-run evals (repeat up to 2 refinement passes)
5. Present task summary + code eval scorecard
6. User approves CODE for this task
7. ON APPROVE → write task report → append phase log → mark task [x] → next task
```

| Step | User approval allowed? |
|------|------------------------|
| 1–4 | **No** — complete eval refinement first |
| 5–6 | **Yes** — present scorecard, then ask |
| 7 | After explicit user Approve only |

## Eval source

| Purpose | Path |
|---------|------|
| **Eval cases** | `evals/code-generation_eval.yaml` |
| **Assertion schema** | `evals/stages/code-generation/eval-spec.yaml` |
| **Do NOT edit** | Eval YAML during forward workflow (read-only; cases added via `/eval-loop`) |

## Step 1 — Resolve filter

From the current task, determine `oape_command`:

| Resolved command | `oape_command` filter |
|------------------|------------------------|
| `/oape:api-generate` | `api-generate` |
| `/oape:api-generate-tests` | `api-generate-tests` |
| `/oape:api-implement` | `api-implement` |
| `/oape:e2e-generate` | `e2e-generate` |
| Manual agent (no OAPE) | `manual` |

Load `evals/code-generation_eval.yaml`. Score only cases where:

- `oape_command` equals the resolved command, **or**
- `oape_command` is `any` (applies to all tasks)

If the file is missing, `evals:` is empty, or no cases match: **skip scoring** and proceed to step 5 (still run OAPE + verify).

## Step 2 — Score each applicable case

For each filtered case in `evals:`:

1. Read case `prompt`, `assertions`, `scoring.pass_threshold`
2. Inspect **fork working copy** — `git diff` for this task, changed files, test output
3. Evaluate against assertion types in `evals/stages/code-generation/eval-spec.yaml`

| Assertion | Check |
|-----------|--------|
| `must_use_pattern` | String/pattern appears in relevant source files |
| `must_not_use` | Pattern absent (e.g. deprecated client.Create) |
| `must_pass_make_targets` | Listed make targets succeeded for this task |
| `must_match_task_payload` | Code aligns with tasks.md §4 for current Task ID |
| `files_must_exist` | Paths exist in fork |
| `files_must_not_exist` | Paths absent |
| `must_follow_constitution` | No constitution violations in generated code |
| `must_follow_effective_go` | Follow `.cursor/skills/effective-go/SKILL.md` |
| `must_include_tests` | Task-appropriate tests present |
| `must_not_violate_non_goals` | Non-goals from task/spec not violated |

Record per case: `pass`, `score` (0–100), `failures[]`.

Overall task code score: average of applicable case scores. Pass if all cases ≥ their `pass_threshold`.

## Step 3 — Write eval results

```
openspec/changes/<change-name>/eval-results/code-generation-<task-id>.yaml
```

```yaml
task_id: T1_3
oape_command: api-implement
stage: code-generation
stage_eval_file: evals/code-generation_eval.yaml
scored_at: <ISO8601>
refinement_rounds: 0
overall_score: 78
overall_pass: false
cases:
  - id: eval-r001-codegen-001
    score: 78
    pass: false
    failures:
      - "must_use_pattern: HandleReconcileResult — not found in pkg/controller/..."
```

Update `refinement_rounds` after each code-fix pass.

## Step 4 — Refine code (mandatory when cases fail)

If **any** case fails, **do not ask for user approval yet**. Loop:

1. Load failed case `prompt` + `assertions`
2. Load current task §4 payload and design-bundle.md
3. **Fix code in fork working copy only** — do not modify approved markdown artifacts
4. Re-run verification (make targets from task Acceptance criteria)
5. Re-score code-generation evals
6. Repeat until **all applicable cases pass** OR **2 refinement passes** exhausted

If still failing after 2 passes: proceed to step 5 with scorecard showing remaining failures; user decides at approval gate.

## Step 5 — Present task summary (code ready for review)

Include:

1. **Files touched** — paths changed in fork for this task
2. **Test results** — acceptance criteria + make targets
3. **Code eval scorecard** — overall %, cases pass/fail, refinement rounds, eval-driven fixes applied
4. **Remaining eval gaps** — if any cases still fail after max refinement passes

## Step 6 — User code approval

Ask (substitute task_id, task_title):

> **Code eval score: {overall_score}%** ({N}/{M} cases pass).  
> Approve the **code changes** for task {task_id} ({task_title}) and proceed to the next task?  
> **(Approve / Reject with feedback)**

- **Approve** → step 7
- **Reject** → add REVISION FEEDBACK to design-bundle; re-run task from step 1 (including full eval gate)

## Step 7 — On approve (record and advance)

1. Mark task `- [x]` in tasks.md
2. Write **`implementation/task-reports/<task-id>.md`** using `templates/implementation-task-report.md`
3. Append section to **`implementation-phase-log.md`** (link to task report)
4. Advance to next pending task

## Guardrails

- **Never** present user approval before running code-generation evals (when applicable cases exist)
- **Never** advance to the next task without user Approve
- Score **code in fork cwd** — not markdown under `openspec/changes/`
- Task reports accumulate under `implementation/task-reports/` for final `implementation-report.md`
