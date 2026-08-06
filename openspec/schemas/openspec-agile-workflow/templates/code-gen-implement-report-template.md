# Code-Gen Implement Report (Solve-Pipeline KPI Gate)

**Change**: [CHANGE_NAME]
**Jira**: [JIRA_KEY]
**Generated**: [ISO8601_DATE]
**Stage start SHA**: [STAGE_START_SHA]
**Final SHA**: [FINAL_SHA]

## Source

This report's gates, thresholds, and metrics come from **two separate
provenance chains** — do not mix them up. See
`stage-gate/SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` for the full provenance and
judge-adoption rationale.

**Source 1 — ai-helpers solve-pipeline KPI set** (hard gates, `solution_correctness`, `code_quality`):

| What | Where |
|------|-------|
| Primary source | `plugins/openshift-developer/evals/eval-solve.yaml`, repo `openshift-eng/ai-helpers` |
| Runner | `plugins/openshift-developer/evals/scripts/run-solve.sh` |
| Merged via | [PR #628](https://github.com/openshift-eng/ai-helpers/pull/628) |
| Superseded predecessor | closed [PR #551](https://github.com/openshift-eng/ai-helpers/pull/551) |
| Case example | [`cases/solve/case-001`](https://github.com/openshift-eng/ai-helpers/tree/main/plugins/openshift-developer/evals/cases/solve/case-001) (OCPBUGS-34662 / HyperShift, known-good [hypershift#7538](https://github.com/openshift/hypershift/pull/7538)) |
| Framework basis | [opendatahub-io/agent-eval-harness](https://github.com/opendatahub-io/agent-eval-harness) `eval.yaml` schema |

**Source 2 — internal repo-specific pattern judges** (`cg01_reuse_over_reinvent`,
`cg04_scope_boundaries`, `cg05_known_good_pattern`, `cg06_build_verify_order`):

| What | Where |
|------|-------|
| Source | This team's own internal pattern-review table ("Generic — other teams can reuse"), **not** ai-helpers or any external repo/PR |
| Rubric doc | [`stage-gate/code-gen-eval-repo-specific.md`](../stage-gate/code-gen-eval-repo-specific.md) |
| Numbering note | `CG-02`/`CG-03` are operator-specific patterns from the same review, out of scope for this gate — hence the gaps in CG-01/04/05/06 |

**Cadence**: hard gates and LLM judges below are scored **once per plan phase**,
not once per task — see the Source doc's "Note on cadence" section for why.
Table 4 (Per-Task Context) is the one exception: it stays per-task since it is
metadata (title/complexity/files), not a gate result.

## Summary

[One paragraph: number of phases scored, overall hard-gate pass rate, overall
LLM mean scores, whether the stage-level `commit_message_format` check passed,
and whether every gate met its threshold. Note if any phase required the
backfill-check recovery path (see Gaps / Deviations).]

## Table 1 — Hard Gates

| Gate | Phases passed | Phases total | Pass rate | Threshold | Meets threshold |
|------|----------------|--------------|-----------|-----------|------------------|
| has_code_changes | [N] | [M] | [N/M]% | min_pass_rate 1.0 | Yes/No |
| make_verify_passes | [N] | [M] | [N/M]% | min_pass_rate 1.0 | Yes/No |
| make_test_passes | [N] | [M] | [N/M]% | min_pass_rate 1.0 | Yes/No |
| coverage_meets_threshold | [N] | [M] | [N/M]% | min_pass_rate 0.8 | Yes/No |
| commit_message_format | [0 or 1] | 1 | [0 or 1]/1 | min_pass_rate 1.0 | Yes/No |

Note: `coverage_meets_threshold` is package coverage (`go tool cover -func`),
computed once per phase across every package the phase touched — not diff
coverage, since this repo does not have the source's `cov-diff` binary.
Stage-wide coverage (stage_start_sha → final SHA): [N]%.

`commit_message_format` is checked once, at stage end, against the real
pre-push commit — not per phase and not per task (see Source rationale).

### Per-phase hard gate detail

| Phase | Tasks in phase | has_code_changes | make_verify_passes | make_test_passes | coverage_meets_threshold |
|-------|-----------------|--------------------|-----------------------|--------------------|----------------------------|
| 1 | T1_1..T1_6 | Pass | Pass | Pass | Pass (61.2%) |

## Table 2 — LLM Quality Judges

**Source 1 (ai-helpers):**

| Judge | Mean score | Threshold | Meets threshold | Phases scored |
|-------|-----------|-----------|------------------|----------------|
| solution_correctness | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] |
| code_quality | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] |

**Source 2 (repo-specific, see [`code-gen-eval-repo-specific.md`](../stage-gate/code-gen-eval-repo-specific.md)):**

| Judge | Mean score | Threshold | Meets threshold | Phases scored | Phases N/A-excluded |
|-------|-----------|-----------|------------------|----------------|-----------------------|
| cg01_reuse_over_reinvent | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] | 0 (never n/a) |
| cg04_scope_boundaries | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] | 0 (never n/a) |
| cg05_known_good_pattern | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] | [K] (no `known_good_pr` reference applied) |
| cg06_build_verify_order | [N.N] / 5 | min_mean 3.5 | Yes/No | [M] | [K] (phase touched nothing generated-code-related) |

`cg05_known_good_pattern` and `cg06_build_verify_order` means are computed
**only across non-n/a phases** — a phase marked `n/a: true` for a judge is
excluded from that judge's mean, not scored as a placeholder.

### Not applicable (documented, not omitted)

| Judge | Status | Rationale |
|-------|--------|-----------|
| solve_quality | N/A | Assumes a distinct "Phase 1: solve" boundary this pipeline does not have |
| review_thoroughness | N/A | Assumes a distinct code-review phase; `/oape:review` is excluded from implementation |
| fix_completeness | N/A | No review-findings artifact exists in this pipeline to grade against |

### Per-phase LLM judge detail

| Phase | solution_correctness | code_quality | cg01_reuse_over_reinvent | cg04_scope_boundaries | cg05_known_good_pattern | cg06_build_verify_order | Notes |
|-------|-----------------------|--------------|---------------------------|--------------------------|----------------------------|----------------------------|-------|
| 1 | 4 | 4 | 5 | 5 | n/a | n/a | cg05/cg06 n/a — no known-good-PR reference; no generated-code changes |

## Table 3 — Execution / Cost KPIs

**These are token-count estimates (tiktoken `cl100k_base`), not billed API cost.**
A Cursor session does not expose the `stream-json` cost field the source's
bash-based `claude -p` harness reads — see `openspec/telemetry/tokens.py`.

| Metric | Value |
|--------|-------|
| Phases scored | [N] |
| Tasks (all phases) | [N] |
| Total input tokens (estimated) | [N] |
| Total output tokens (estimated) | [N] |
| Total refinement rounds (all tasks) | [N] |
| Stage wall-clock duration | [N]s or [N]m |
| `max_budget_usd` / `timeout` caps | N/A — no per-invocation cost/time cap enforced in this pipeline (see Source: caps exist in the reference harness's `execution:` block, not adopted here) |

### Per-phase cost/execution detail

| Phase | Input tokens (est.) | Output tokens (est.) | Refinement rounds | Tasks in phase |
|-------|----------------------|------------------------|---------------------|------------------|
| 1 | [N] | [N] | [N] | [N] |

## Table 4 — Per-Task Context

This table stays **per-task** (not per-phase) — it is metadata for traceability,
not a Solve-Pipeline KPI gate result.

| Task ID | Phase | Title | Complexity (difficulty proxy) | Category | Target files | Known-good PR |
|---------|-------|-------|--------------------------------|----------|---------------|-----------------|
| T1_1 | 1 | [title] | [1\|2\|3\|5\|8] | [bug\|feature\|refactor] | [path, path] | N/A |

`Category` is derived from the parent Jira issue type in `inputs/jira.yaml`.
`Known-good PR` is `N/A` unless this task's Jira issue references a prior,
already-merged fix for the same defect class.

## Table 5 — Output Artifacts / Evidence Trail

| Artifact | Path |
|----------|------|
| Per-phase hard-gate + LLM judge results | `eval-results/solve-kpi-phase-<N>.yaml` (one per phase) |
| Existing code-generation eval results (separate gate, per task) | `eval-results/code-generation-<task-id>.yaml` |
| Per-task implementation report | `implementation/task-reports/<task-id>.md` |
| Commit log (stage_start_sha → final SHA) | `git log --oneline <stage_start_sha>..HEAD` |
| Telemetry events | `openspec/changes/<change>/telemetry/events.jsonl` |
| This report | `implementation/code-gen-implement-report.md` |

## Gaps / Deviations from the Source Harness

- No `cov-diff` binary — coverage is package-level, not diff-level, computed
  once per phase.
- No per-task or per-phase git commit — `commit_message_format` is a
  stage-end check, not a hard gate scored earlier.
- No `solve_quality` / `review_thoroughness` / `fix_completeness` — no
  Solve→Review→Fix phase split exists in `/opsx-apply`.
- No real API cost — token/cost figures are tiktoken-based estimates.
- No `max_budget_usd` / `timeout` enforcement — informational only, not adopted
  as a hard cap in this pipeline.
- Cadence: scored once per plan phase (grouped by task-ID prefix `T<n>_`), not
  once per task, unlike the source harness which scores one `solve` run per
  Jira issue — see Source section above.
- `cg05_known_good_pattern` / `cg06_build_verify_order` are excluded from
  their stage-wide mean for any phase marked `n/a` (no known-good-PR
  reference applied / no generated-code changes in the phase) — see Table 2.
- `cg01_reuse_over_reinvent` / `cg04_scope_boundaries` / `cg05_known_good_pattern`
  / `cg06_build_verify_order` come from this team's internal pattern-review
  table (Source 2), not from `openshift-eng/ai-helpers` — do not conflate
  their provenance with the PR #628 judges above.
- [List any phase whose result required the mandatory backfill-check recovery
  path (SHA fallback instead of a recorded `phase_shas.<N>.start_sha`) — name
  the phase, the fallback used, and why the live trigger missed it, or state
  "None — every phase's gate ran at its live trigger point."]
