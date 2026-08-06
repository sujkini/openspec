# Solve-Pipeline KPI Eval Gate — Independent gate for `/opsx-apply`

Score generated code against the **ai-helpers solve-pipeline KPI set** — a second,
independent eval gate that runs alongside (not instead of) the existing
`code_generation_eval_gate`. This gate is mode-agnostic: it runs for both
`codegen_mode: direct` and `codegen_mode: ai-helpers`.

**Cadence: ONCE PER PLAN PHASE, never per task.** A "phase" is the leading
numeral of a task ID (`T<n>_<m>` → phase `n`), matching `tasks.md` §2/§3
grouping. This applies in both `task_execution_mode` values — phase-iterative
has an explicit `PHASE_COMPLETE` state per phase; one-shot has no such state
but still groups tasks the same way, so phase boundaries are detected from
task-ID-prefix transitions during the task loop.

Paths below are relative to the schema root (`openspec/schemas/openspec-agile-workflow/`
when installed).

## Source (do not lose this when copying/refactoring this file)

**Two separate provenance chains feed this gate. Do not mix them up when
citing sources — see each subsection below.**

### Source 1 — ai-helpers solve-pipeline KPI set (C1–C6)

Every gate and threshold in C1–C6 is taken from real, merged code — not invented:

| What | Where |
|------|-------|
| Primary source (judges + thresholds) | [`plugins/openshift-developer/evals/eval-solve.yaml`](https://github.com/openshift-eng/ai-helpers/blob/main/plugins/openshift-developer/evals/eval-solve.yaml), repo `openshift-eng/ai-helpers` |
| Runner that produces the raw metrics | [`plugins/openshift-developer/evals/scripts/run-solve.sh`](https://github.com/openshift-eng/ai-helpers/blob/main/plugins/openshift-developer/evals/scripts/run-solve.sh) |
| Merged via | [PR #628](https://github.com/openshift-eng/ai-helpers/pull/628) "feat(openshift-developer): Add evals and move solve skill from jira plugin" (2026-07-27) |
| Superseded predecessor | closed [PR #551](https://github.com/openshift-eng/ai-helpers/pull/551) — earlier `plugins/jira/evals/eval-solve-pipeline.yaml`, same 10 judges/thresholds |
| Case example | [`plugins/openshift-developer/evals/cases/solve/case-001`](https://github.com/openshift-eng/ai-helpers/tree/main/plugins/openshift-developer/evals/cases/solve/case-001) — OCPBUGS-34662 (HyperShift), grounded against known-good [hypershift#7538](https://github.com/openshift/hypershift/pull/7538) |
| Framework basis | [opendatahub-io/agent-eval-harness](https://github.com/opendatahub-io/agent-eval-harness) `eval.yaml` schema (judges/thresholds/traces conventions) |
| Sibling reference (context only, not the metrics source) | [PR #649](https://github.com/openshift-eng/ai-helpers/pull/649) — TRT jira-solver eval cases |

### Source 2 — internal repo-specific pattern judges (C7–C10)

C7–C10 (`cg01_reuse_over_reinvent`, `cg04_scope_boundaries`,
`cg05_known_good_pattern`, `cg06_build_verify_order`) are **NOT** from
ai-helpers or any external repo/PR. They come from this operator team's own
internal pattern-review table of recurring code-gen mistakes ("Generic —
other teams can reuse" set; `CG-02`/`CG-03` are operator-specific patterns
from the same review and are out of scope here, which is why the numbering
has gaps). Full rubric: [`code-gen-eval-repo-specific.md`](code-gen-eval-repo-specific.md).
Never cite an ai-helpers PR number for C7–C10.

**Note on cadence**: the source harness scores each `solve` invocation
individually (its unit of work is one Jira issue = one task). This operator's
`/opsx-apply` decomposes one Jira issue into many small tasks grouped into
plan phases, so the natural unit of work here is the **phase**, not the
individual task — scoring every task would over-count and add cost/noise
without adding signal, since tasks within a phase share the same objective.

## Judge adoption map

The ai-helpers source defines 10 judges (5 deterministic hard gates + 5 LLM
judges). Here is what happened to each one in this operator's `/opsx-apply`
pipeline, plus 4 additional internally-sourced LLM judges layered on top
(see Source 2 above) that have no ai-helpers counterpart:

| Source judge | Status | Our equivalent | Rationale |
|---|---|---|---|
| `has_code_changes` | Adopted | Non-empty diff since `phase_shas.<N>.start_sha`, scored once per phase | Direct port, phase-scoped |
| `make_verify_passes` | Adopted | Pass only if every task in the phase individually passed verify (read from each task's `completed[]` entry) | No duplicate execution — reuses per-task results, aggregated once per phase |
| `make_test_passes` | Adopted | Pass only if every task in the phase individually passed tests (read from each task's `completed[]` entry) | No duplicate execution — reuses per-task results, aggregated once per phase |
| `coverage_meets_threshold` | Adapted | `go tool cover -func` total percentage across every package touched anywhere in the phase vs `config.yaml → flags.min_diff_coverage_pct` | Source uses `cov-diff` (changed-line coverage); this repo does not ship that binary, so package-level coverage is used as an approximation. Computed once per phase, not per task. |
| `commit_message_format` | Adapted | Conventional-commit regex against the **existing single pre-push commit** (`fork_repo.draft_pr` step) | This pipeline does not commit per task or per phase (only once, before push) — checked once, at stage end |
| `solve_quality` | N/A | — | Assumes a distinct "Phase 1: solve" boundary this pipeline does not have |
| `review_thoroughness` | N/A | — | Assumes a distinct code-review phase; `/oape:review` is explicitly excluded from implementation (`oape_routing.do_not_invoke_during_implementation`) |
| `fix_completeness` | N/A | — | Assumes review findings text to grade against; no such artifact exists here |
| `solution_correctness` | Adopted | LLM 1–5 rubric vs the phase's tasks' combined Acceptance Criteria / Jira intent, scored once per phase against the whole-phase diff | Maps directly to final-output correctness |
| `code_quality` | Adopted | LLM 1–5 rubric, idiomatic Go / error handling / test quality, scored once per phase against the whole-phase diff | Maps directly |
| cost/token/duration metrics | Adapted | `openspec/telemetry/tokens.py` tiktoken-based estimates, aggregated per phase and per stage | Source reads real `stream-json` cost fields from a scripted `claude -p` CLI harness; a Cursor session has no equivalent field, so these are **estimates, not billed cost** — always label them as such |
| *(no ai-helpers counterpart)* `cg01_reuse_over_reinvent` | Added (internal source) | LLM 1–5 rubric, reuse-over-reinvent (API + non-API), scored once per phase | See Source 2 — [`code-gen-eval-repo-specific.md`](code-gen-eval-repo-specific.md) |
| *(no ai-helpers counterpart)* `cg04_scope_boundaries` | Added (internal source) | LLM 1–5 rubric, scope creep / forbidden areas, scored once per phase | See Source 2 |
| *(no ai-helpers counterpart)* `cg05_known_good_pattern` | Added (internal source) | LLM 1–5 rubric, known-good-pattern divergence, scored once per phase, N/A-excludable | See Source 2 |
| *(no ai-helpers counterpart)* `cg06_build_verify_order` | Added (internal source) | LLM 1–5 rubric, generate-before-test ordering, scored once per phase, N/A-excludable | See Source 2 |

## Mandatory sequence

```
BEFORE (once, first task of the stage):
  1. Capture stage_start_sha
BEFORE (once per phase, first task of that phase):
  2. Capture phase_shas.<N>.start_sha
BACKFILL CHECK (every single /opsx-apply invocation, before anything else):
  3. Compare fully-completed phases in tasks.md against
     solve_kpi_gate_completed_phases in state.yaml
  4. If any completed phase is missing from that list, run steps 5-8 for it
     NOW, before handling whatever state.yaml says the current state is
PER-PHASE (phase-iterative: at PHASE_COMPLETE; one-shot: at each task-ID-prefix
transition, and once more for the final phase when all tasks are done):
  5. Run 4 hard gates (has_code_changes, make_verify_passes, make_test_passes,
     coverage_meets_threshold) against the WHOLE PHASE diff
  6. Run 6 LLM judges (solution_correctness, code_quality, cg01_reuse_over_reinvent,
     cg04_scope_boundaries, cg05_known_good_pattern, cg06_build_verify_order)
     against the WHOLE PHASE diff — cg05/cg06 may be n/a for a given phase
  7. Write eval-results/solve-kpi-phase-<N>.yaml
  8. Append N to state.yaml → solve_kpi_gate_completed_phases
AFTER (once, stage end — all tasks/phases complete, immediately before push):
  9. Re-run the backfill check (step 3-4) — refuse to proceed if any gap remains
  10. Run commit_message_format against the real pre-push commit
  11. Compute stage-wide coverage (stage_start_sha → HEAD)
  12. Aggregate every solve-kpi-phase-*.yaml + telemetry into
      implementation/code-gen-implement-report.md
```

## Step A — BEFORE

### A1. Stage start SHA (first task only)

On the very first task executed in this invocation of the Implementation Stage
(i.e., `state.yaml` has no `stage_start_sha` yet), in the fork/working copy:

```bash
git rev-parse HEAD
```

Write the result to `state.yaml → stage_start_sha`. Do not overwrite it on later tasks.

### A2. Phase start SHA (once per phase, not per task)

Immediately before executing the **first** task of a given phase — i.e., when
`state.yaml → phase_shas.<N>.start_sha` does not yet exist for the phase number
`N` of the task about to run:

```bash
git rev-parse HEAD
```

Store as `phase_shas.<N>.start_sha` in `state.yaml`. This is the baseline the
phase's hard gates diff against once the whole phase is done. Do **not**
capture a new SHA for every task within the same phase — only once, at the
phase's first task.

## Step B — BACKFILL CHECK (mandatory, every invocation)

This step exists because a prior implementation of this gate embedded the
per-phase trigger only inline in the linear task-execution flow, and an agent
resuming a session mid-way (or handling many tasks in a batch/auto-approve
loop) sometimes prioritized code+tests and skipped the eval steps entirely for
phases after the first. This step makes that failure mode self-correcting:
**every single invocation of `/opsx-apply`, in any state, must run this check
before doing anything else** — including before resuming an in-progress task,
before handling an approval, and before advancing a phase.

1. Read `tasks.md` §3. Compute `fully_completed_phases` = every phase number
   `N` such that **all** task IDs with prefix `T<N>_` are marked `- [x]`.
2. Read `state.yaml → solve_kpi_gate_completed_phases` (treat as `[]` if the
   field is absent — older state files predate this field).
3. Compute `missing = fully_completed_phases - solve_kpi_gate_completed_phases`,
   sorted ascending.
4. If `missing` is empty, or `config.yaml → flags.solve_pipeline_kpi_eval` is
   `false`, proceed immediately to the orchestrator's normal state handling.
5. Otherwise, for each phase `N` in `missing` (in order), run Step C (below)
   for that phase using this SHA fallback order for
   `phase_shas.<N>.start_sha` (needed because older runs, or the very gap
   being repaired, may not have recorded it):
   - (a) `state.yaml → phase_shas.<N>.start_sha`, if present — use it.
   - (b) `state.yaml → phase_shas.<N-1>.end_sha`, if phase `N-1` already has a
     recorded gate result — use it (the previous phase's end is this phase's
     start).
   - (c) `stage_start_sha`, but scope the diff to only the **Target files**
     listed for phase `N`'s tasks in `tasks.md` §4 (best-effort — this
     necessarily over- or under-counts if other phases touched the same
     files; document this explicitly as a caveat in that phase's
     `solve-kpi-phase-<N>.yaml` and in the final report's Gaps section).
6. After scoring, record `phase_shas.<N>.end_sha = <current HEAD>` and append
   `N` to `solve_kpi_gate_completed_phases`.
7. Only once every entry in `missing` has been backfilled, proceed to the
   orchestrator's normal state handling for this invocation.

**Hard rule**: never advance `current_plan_phase`, never set state `COMPLETE`,
and never write `code-gen-implement-report.md` while `missing` (recomputed at
that point) is non-empty.

## Step C — PER-PHASE (the actual gate, run once per phase)

Triggered by (a) `PHASE_COMPLETE` in phase-iterative mode, immediately after
the last task of the phase is approved; (b) in one-shot mode, when the next
pending task's phase number differs from the just-completed task's phase
number, and once more for the final phase when all tasks are done; or (c) by
Step B (backfill) for a phase that was missed.

### C1. `has_code_changes` (hard gate)

```bash
git diff <phase_shas.N.start_sha> -- .
```

Pass if the diff is non-empty. Fail message: "No code changes produced by
Phase N."

### C2. `make_verify_passes` (hard gate)

Read `verify_status` from every task's entry in `state.yaml → completed[]`
whose `task_id` has prefix `T<N>_`. Pass only if every one of them is
`passed` (or `skipped`, which counts as pass). Do **not** re-run `go vet` /
`make verify` — this is an aggregation of results already captured per task.

### C3. `make_test_passes` (hard gate)

Same as C2 but for `test_status`. Pass only if every task in the phase has
`test_status: passed` or `skipped`.

### C4. `coverage_meets_threshold` (hard gate)

Across every package touched by any task in the phase (union of `files_changed`
for all `T<N>_*` tasks, excluding `_test.go`):

```bash
go test -coverprofile=/tmp/solve-kpi-phase-<N>-cover.out ./<pkg1>/... ./<pkg2>/... ...
go tool cover -func=/tmp/solve-kpi-phase-<N>-cover.out
```

Parse the `total:` line's percentage. Compare against
`config.yaml → flags.min_diff_coverage_pct` (default `40`). Pass if
`percentage >= threshold`. If no `.go` files changed anywhere in the phase,
record `"No Go source files changed in this phase — gate skipped (counts as pass)"`.

**Note in the result**: this is package coverage, not diff coverage — the
source's `cov-diff` tool is not available here (see Judge adoption map above).

### C5. `solution_correctness` (LLM judge, 1–5, not blocking)

Score the whole phase's diff (`phase_shas.<N>.start_sha` → current) against
the combined Objective and Acceptance Criteria of every task in the phase
(`tasks.md` §4), and the parent Jira intent from `inputs/jira.yaml` when
available:

- 1: Does not address the phase's tasks at all, or introduces new bugs.
- 2: Partially addresses the phase's tasks with significant gaps.
- 3: Addresses the core objectives correctly with minor gaps.
- 4: Correctly and completely addresses the phase's objectives with good tests.
- 5: Excellent — correct, complete, well-tested, matches or exceeds intent.

Threshold: `min_mean: 3.5` (evaluated across all phases at stage end — a
single phase scoring below 3.5 does not block that phase, it lowers the
stage average).

### C6. `code_quality` (LLM judge, 1–5, not blocking)

Score the whole phase's diff for idiomatic Go, proper error handling, and
test quality:

- 1: Broken code or fundamental Go mistakes.
- 2: Works but no error handling, no tests, non-idiomatic.
- 3: Acceptable — compiles, passes tests, room for improvement.
- 4: Good — idiomatic Go, proper error handling, meaningful tests.
- 5: Excellent — clean, idiomatic, well-tested, proper godoc.

Threshold: `min_mean: 3.5` (same aggregation rule as C5).

### C7. `cg01_reuse_over_reinvent` (LLM judge, 1–5, not blocking)

Full detection algorithm and scoring rubric (two sub-checks — API reuse via
the 100%-coverage rule, and non-API file/folder creation necessity):
[`code-gen-eval-repo-specific.md` § CG-01](code-gen-eval-repo-specific.md#cg-01--reuse-over-reinvent-two-sub-checks-one-combined-score).

Threshold: `min_mean: 3.5` (same aggregation rule as C5). Never `n/a`.

### C8. `cg04_scope_boundaries` (LLM judge, 1–5, not blocking)

Full detection algorithm and scoring rubric (declared scope vs. non-goals vs.
repo-specific forbidden areas):
[`code-gen-eval-repo-specific.md` § CG-04](code-gen-eval-repo-specific.md#cg-04--scope-creep--forbidden-areas).

Threshold: `min_mean: 3.5` (same aggregation rule as C5). Never `n/a`.

### C9. `cg05_known_good_pattern` (LLM judge, 1–5, not blocking, N/A-excludable)

Full detection algorithm and scoring rubric:
[`code-gen-eval-repo-specific.md` § CG-05](code-gen-eval-repo-specific.md#cg-05--known-good-pattern-ignored).

If no `known_good_pr`-style reference applies to this phase (the common
case), write `n/a: true` instead of a score — **exclude n/a phases from the
stage-wide mean**, do not default to a placeholder score. Threshold (when
not n/a): `min_mean: 3.5`.

### C10. `cg06_build_verify_order` (LLM judge, 1–5, not blocking, N/A-excludable)

Full detection algorithm and scoring rubric (real Makefile target graph:
`generate: op-generate go-generate openapi-generate manifests`, must run
before tests that depend on generated code):
[`code-gen-eval-repo-specific.md` § CG-06](code-gen-eval-repo-specific.md#cg-06--buildverify-order).

If the phase touched nothing generated-code-related, write `n/a: true`
instead of a score — **exclude n/a phases from the stage-wide mean**.
Threshold (when not n/a): `min_mean: 3.5`.

### C11. Write per-phase result

```
openspec/changes/<name>/eval-results/solve-kpi-phase-<N>.yaml
```

```yaml
phase: 3
stage: solve-pipeline-kpi
scored_at: <ISO8601>
phase_start_sha: <sha>
phase_end_sha: <sha>
tasks_in_phase: [T3_1, T3_2, T3_3, T3_4, T3_5, T3_6]
backfilled: false   # true if this ran via Step B (backfill check) instead of the live trigger
sha_fallback_used: none   # or "phase_n_minus_1_end" / "stage_start_scoped_to_target_files" — only when backfilled
hard_gates:
  has_code_changes: {pass: true, detail: "diff has 612 lines across 6 tasks"}
  make_verify_passes: {pass: true, detail: "6/6 tasks passed verify"}
  make_test_passes: {pass: true, detail: "6/6 tasks passed tests"}
  coverage_meets_threshold: {pass: true, detail: "phase package coverage 58.3% >= 40%"}
overall_hard_gate_pass: true
llm_judges:
  solution_correctness: {score: 4, rationale: "..."}
  code_quality: {score: 4, rationale: "..."}
  cg01_reuse_over_reinvent: {score: 5, rationale: "..."}
  cg04_scope_boundaries: {score: 5, rationale: "..."}
  cg05_known_good_pattern: {n/a: true, reason: "no known_good_pr reference for this phase"}
  cg06_build_verify_order: {n/a: true, reason: "phase touched no api/v1alpha1 types or generated artifacts"}
```

Hard-gate failures at phase level are recorded and surfaced in the phase
summary / final report — they do **not** trigger a refinement loop (each
task's own 2-pass refinement budget was already spent per task before the
phase was marked complete) and they do not block advancing to the next
phase, unless the user explicitly stops to fix them.

### C12. Update state

Append `N` to `state.yaml → solve_kpi_gate_completed_phases`. If this run
came from the live trigger (not backfill), also record
`phase_shas.<N>.end_sha = <current HEAD>`.

## Step D — AFTER (stage end, once — all tasks/phases complete)

Runs at the exact point `implementation-report.md` is written (one-shot: all
tasks marked `- [x]`; phase-iterative: all phases done) — **before** the push
step in `fork_repo.draft_pr`.

### D0. Re-run the backfill check (Step B)

Before anything else in this section, recompute `missing` (Step B, steps 1–3).
If non-empty, backfill it now. Do not proceed to D1 while gaps remain.

### D1. `commit_message_format` (hard gate, blocking)

At the existing "stage and commit any remaining changes with a descriptive
message referencing jira_key" step, before running `git push`:

```
Pattern: ^(feat|fix|refactor|chore|test|docs|style|perf|ci|build|revert)(\(.+?\))?:
```

Check the message against the pattern. If it fails, **rewrite the commit message**
to conform (do not change the diff) and re-check before proceeding to push. Do not
introduce a new commit — amend the existing one.

### D2. Stage-wide coverage

```bash
git diff stage_start_sha --name-only -- '*.go' | grep -v _test.go | xargs -I{} dirname {} | sort -u
go test -coverprofile=/tmp/solve-kpi-stage-cover.out <changed-packages>
go tool cover -func=/tmp/solve-kpi-stage-cover.out
```

Record the `total:` percentage as the stage-level coverage figure (separate
from each phase's individual C4 result — this is the whole-stage rollup).

### D3. Aggregate and write the report

Read every `eval-results/solve-kpi-phase-*.yaml` written during Step C (one
per phase, not one per task), plus:
- `openspec/telemetry/tokens.py` estimates (`estimate_task_tokens` summed per
  phase, `estimate_phase5_tokens` for the stage total)
- `tasks.md` §3/§4 for per-task context table (complexity, target files,
  assigned agent) — this table remains per-task since it is metadata, not a
  gate result
- `inputs/jira.yaml` for issue type/category

Write `openspec/changes/<name>/implementation/code-gen-implement-report.md`
using `templates/code-gen-implement-report-template.md`. See that template
for the required table structure (per-phase gate rows, per-task context
rows). Write this report **immediately alongside** `implementation-report.md`
(same trigger point, same step).

## Guardrails

- This gate never modifies `evals/code-generation_eval.yaml` (eval-loop-owned) —
  it is fully independent, its own result files, its own report.
- **Cadence discipline**: all 4 hard gates and all 6 LLM judges (C1–C10) are
  scored ONCE PER PHASE. Never score them per task — that reintroduces the
  cost/noise problem this redesign fixed.
- **Don't misattribute provenance.** C1–C6 are from the ai-helpers
  `eval-solve.yaml` (Source 1); C7–C10 (`cg01`/`cg04`/`cg05`/`cg06`) are from
  this team's own internal pattern-review table (Source 2), not from
  ai-helpers or any external PR. Never cite an ai-helpers PR number for
  C7–C10, and always keep the two provenance chains separate in the final
  report's Source table.
- **N/A-exclusion rule for `cg05_known_good_pattern` / `cg06_build_verify_order`**:
  when a phase has no applicable reference (cg05) or touched nothing
  generated-code-related (cg06), record `n/a: true` for that phase and
  exclude it from the stage-wide mean for that judge — never default a
  missing case to a placeholder score, and never silently drop the field.
- **Never skip the backfill check.** It is not optional and not just for
  phase boundaries — it runs at the START of every invocation, in every
  state, before anything else. This is the mechanism that prevents a missed
  phase from staying missed.
- Never re-run `go vet`/`go test`/`make verify`/`make test` for C2/C3 —
  aggregate the exit codes already captured by each task's existing
  verify/test steps.
- Always label cost/token figures as estimates (tiktoken-based), never as
  billed USD cost.
- Always list `solve_quality`, `review_thoroughness`, `fix_completeness` as
  N/A with their rationale in the final report — never omit them silently.
- `coverage_meets_threshold` is package coverage, not diff coverage — always
  say so in both the per-phase result and the final report.
- `commit_message_format` runs once, at stage end, against the real commit
  that is about to be pushed — never invent a per-task or per-phase commit
  to check instead.
- If `config.yaml → flags.solve_pipeline_kpi_eval` is `false`, skip this
  entire gate (Steps A–D, including the backfill check) but still run
  `code_generation_eval_gate` and all mandatory verification/test steps
  normally.
