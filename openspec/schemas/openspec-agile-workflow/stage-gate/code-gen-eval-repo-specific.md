# Code-Gen Eval — Repo-Specific Generic Judges (CG-01, CG-04, CG-05, CG-06)

Rubric source-of-truth for 4 additional per-phase LLM judges scored by the
**Solve-Pipeline KPI Eval Gate** (`solve_pipeline_kpi_eval_gate`), alongside
`solution_correctness` and `code_quality`. See
[SOLVE_PIPELINE_KPI_EVAL_PROMPT.md](SOLVE_PIPELINE_KPI_EVAL_PROMPT.md) Step C
for when/how this file is invoked — that file is the orchestration doc, this
file is the detailed scoring rubric these 4 judges delegate to.

## Source

**This is NOT sourced from `openshift-eng/ai-helpers` or any external repo/PR.**
These 4 judges come from an internal pattern-review table ("Generic — other
teams can reuse", split from an "operator-specific" counterpart table) drafted
during this operator team's own retrospective on recurring code-gen mistakes.
The `CG-<NN>` numbering is preserved from that review as-is — it is not
sequential here because `CG-02`/`CG-03` are operator-specific patterns from
the same review, not part of this generic set, and are out of scope for this
gate.

Do not cite an ai-helpers PR number for these 4 judges. Keep this provenance
chain separate from the ai-helpers-sourced judges everywhere both appear
(schema `provenance` block, `SOLVE_PIPELINE_KPI_EVAL_PROMPT.md` Source
section, report template Source table).

## Judge summary

| CG-ID | Judge ID | Pattern | Blocking | Threshold |
|-------|----------|---------|----------|-----------|
| CG-01 | `cg01_reuse_over_reinvent` | Reinvent instead of reuse existing helpers/APIs | No (advisory, scored) | `min_mean: 3.5` |
| CG-04 | `cg04_scope_boundaries` | Scope creep / touch forbidden areas | No (advisory, scored) | `min_mean: 3.5` |
| CG-05 | `cg05_known_good_pattern` | Ignore known-good pattern when a reference exists | No (advisory, scored, N/A-excludable) | `min_mean: 3.5` |
| CG-06 | `cg06_build_verify_order` | Wrong build/verify order | No (advisory, scored, N/A-excludable) | `min_mean: 3.5` |

All 4 are scored **once per plan phase** (same cadence as `solution_correctness`
/ `code_quality` — never per task), against the whole phase's diff
(`phase_shas.<N>.start_sha` → current HEAD/working tree). None of the 4 are
hard gates — a low score is surfaced in the phase summary and the final
`code-gen-implement-report.md`, but does not block advancing to the next
phase or block task approval, unless the user explicitly stops to address it.

---

## CG-01 — Reuse over reinvent (two sub-checks, one combined score)

**Pattern**: agent reinvents functionality instead of reusing an existing
helper/API already in the repo.

This judge has two distinct sub-checks with different rules — read both
before scoring.

### Sub-check A — API reuse (100%-coverage rule)

Applies when the phase's diff introduces a **new exported function or type**
(a genuine API surface: exported symbol in a package, not a private helper).

1. Identify the new exported symbol(s) added in the phase's diff.
2. Search the repo for a **pre-existing** exported symbol with equivalent
   capability — same problem domain, similar signature/purpose. Look in the
   package families most likely to already have overlapping helpers for this
   repo: `pkg/obfuscate/`, `controllers/mustgather/*.go` (e.g. `template.go`,
   `conditions.go`, `constant.go`), `pkg/k8sutil/`, `pkg/localmetrics/`,
   `build/bin/upload`. Also check `repo-assessment.md`'s "reusable assets"
   section for this change, if present — it may already have identified
   candidates.
3. If a candidate exists: measure **that specific existing function's**
   coverage, not the whole package's:
   ```bash
   go test -coverprofile=/tmp/cg01-<pkg>.out ./<pkg>/...
   go tool cover -func=/tmp/cg01-<pkg>.out
   ```
   Find the line for the candidate function by name in the `-func` output —
   it reports per-function percentages, not just a package total.
4. **Only if that existing function is at exactly 100.0% coverage** is reuse
   considered mandatory. This is a deliberate, narrow rule: an existing
   function must be proven fully exercised by tests before treating "should
   have reused it" as a real finding — reusing a partially-tested existing
   function carries its own risk, so partial coverage (< 100%) means writing
   new, tested code was an acceptable choice, **not** a violation.
5. **Violation** = a pre-existing, 100%-covered equivalent existed and the
   phase duplicated its logic instead of calling it.
6. **No violation** = no equivalent candidate exists, OR a candidate exists
   but is below 100% coverage.

### Sub-check B — Non-API reuse (file/folder creation necessity)

Applies to everything else the phase created that is **not** a new public
API: new package directories, new shell/build scripts, new config/YAML
files, new test-helper files, new example manifests.

For each new file or folder introduced in the phase:
1. Check whether an existing file in the same area (same directory, same
   logical component) could have been extended instead of creating a new
   one. Use the phase's own **Target files** (`tasks.md §4`) and
   `repo-assessment.md`'s reusable-assets listing as the necessity signal —
   if the task's own payload already named an existing file to modify and
   the agent created a new one instead without justification, that is a
   strong signal of unnecessary creation.
2. Some new-file creation is inherently necessary and should NOT be flagged:
   a first `_test.go` for a package that had none, a new controller/API
   package that genuinely doesn't exist yet, a new example CR demonstrating
   a new feature. Judge necessity relative to what the task actually asked
   for, not file creation in the abstract.
3. **Violation** = a new file/folder was created where an existing one in
   the same area was suitable and was not used, with no stated rationale.

### Scoring (1-5)

- **5**: No unnecessary reinvention (sub-check A) and no unnecessary new
  files/folders (sub-check B) found in this phase.
- **4**: One minor instance in either sub-check, low impact.
- **3**: A clear violation in one sub-check with moderate impact (e.g. one
  duplicated fully-tested helper, or one clearly avoidable new file).
- **2**: Multiple violations, or one violation with meaningful duplication cost.
- **1**: Pervasive reinvention/unnecessary file creation across the phase.

Rationale **must name the specific existing symbol/file** that should have
been reused (sub-check A) or the specific new file/folder judged unnecessary
and what it should have extended instead (sub-check B). Do not give a vague
score without naming the concrete instance(s).

---

## CG-04 — Scope creep / forbidden areas

**Pattern**: agent touches files outside the task's declared scope, or
inside areas the workflow itself should never modify during code generation.

1. Compute the phase's full changed-files list (`git diff phase_shas.<N>.start_sha -- .`).
2. Compute the **declared scope** = union of every task's **Target files**
   in the phase (`tasks.md §4`), plus files required to co-generate tests
   for those targets (e.g. matching `_test.go`, `fakes/`, `test_utils.go` —
   already expected by `CODE_GENERATION_EVAL_PROMPT.md` Step 4).
3. Compute the **non-goals** = union of every task's stated non-goals in the
   phase (`tasks.md §4`).
4. Compute the repo-specific **forbidden areas** for code-gen phases (these
   are workflow-tooling paths, never legitimate task targets during
   implementation):
   - `openspec/` (this workflow's own change tracking/schemas)
   - `.cursor/` (commands, skills, rules)
   - `eval-generation/` (eval-authoring pipeline)
   - `boilerplate/` (vendored Makefile system — only `boilerplate-update`
     target may touch it, never a code-gen task)
   - `vendor/` (only legitimate for an explicit dependency-vendoring task,
     e.g. `go mod vendor` after a `go.mod` change task)
   - `dashboard/` (separate tool, not part of the operator itself, unless a
     phase's tasks explicitly target it)
5. **Violation** = a changed file is outside the declared scope AND inside a
   forbidden area, OR a changed file explicitly does something a task's
   non-goals said not to do.

### Scoring (1-5)

- **5**: Every changed file is within declared scope; no forbidden areas
  touched; no non-goals violated.
- **4**: One incidental out-of-scope touch with negligible impact (e.g. a
  whitespace-only fix in an adjacent file).
- **3**: One clear scope violation (touched a file not in any task's Target
  files, not forbidden-area, but genuinely out of scope).
- **2**: A forbidden area was touched, or a non-goal was explicitly violated.
- **1**: Multiple forbidden-area touches or repeated non-goal violations.

Rationale must list the specific file path(s) and which rule each one broke.

---

## CG-05 — Known-good pattern ignored

**Pattern**: a known-good, already-merged reference solution exists for a
similar problem, and the agent ignored its established pattern without
justification.

1. Check whether the phase's parent Jira issue (`inputs/jira.yaml`) or any
   task in the phase references a prior similar fix — this repo does not yet
   have a formal `known_good_pr` catalog/field (see
   `code-gen-implement-report-template.md` Table 4, currently always `N/A`
   in practice), so this will usually come from: (a) an explicit mention in
   the Jira description/comments fetched via Jira MCP, (b) a task's own
   Implementation Notes citing a prior PR, or (c) the agent's own repo
   history search (`git log --oneline --grep=<related-keyword>`) turning up
   an applicable merged commit/PR for the same defect class.
2. If a reference is found: diff the phase's approach against that
   reference's shape/pattern (same file(s) touched, same fix strategy).
   **Violation** = the phase diverges from the established pattern with no
   rationale recorded in that task's Deviations section.
3. If no reference is found or applies to this phase (expected to be the
   **common case** in this repo currently): do not force a score.

### No-reference handling (important)

When CG-05 has no applicable reference for a phase, write
`n/a: true` for this judge in that phase's `solve-kpi-phase-<N>.yaml` and
**exclude that phase from the stage-wide mean** for `cg05_known_good_pattern`
— do not default it to a 5 or any other placeholder score. Forcing a score
when there is nothing to compare against would artificially inflate (or
deflate) the mean and hide the fact that this repo doesn't yet have a
known-good-PR catalog to check against.

### Scoring (1-5, only when a reference applies)

- **5**: Followed the known-good pattern closely, or deviated with clear,
  recorded rationale.
- **3**: Partial alignment, some unexplained divergence.
- **1**: Directly contradicts the known-good approach with no rationale.

---

## CG-06 — Build/verify order

**Pattern**: generated code/manifests were not regenerated before
depending on them (tests run against stale generated code, or generated
files were hand-edited instead of regenerated).

This repo's real target graph (`boilerplate/openshift/golang-osd-operator/standard.mk`):

```
generate: op-generate go-generate openapi-generate manifests
test: go-test
go-test: setup-envtest   # compiles and runs the module — needs generated code present
```

I.e. `make generate` runs, in order, `op-generate` → `go-generate` →
`openapi-generate` → `manifests`. Anything that depends on generated
deepcopy code, OpenAPI defs, or CRD manifests must have `make generate`
(or the specific sub-target, e.g. `make manifests`) run and succeed
**before** `go test` / `make test` is run against that code.

1. Identify whether any task in the phase touched `api/v1alpha1/*_types.go`,
   added/changed kubebuilder markers, or otherwise affects generated
   artifacts (deepcopy, CRD YAML, OpenAPI schema, RBAC manifests).
2. If yes: confirm the phase's task-report / eval-results history shows
   `make generate` (or `make manifests`) was run and passed **before** the
   `go test` invocation(s) for that phase's tasks that depend on the
   generated code (deepcopy methods, updated CRD schema in tests).
3. **Violation** = tests were run first (or generated artifacts were never
   regenerated) and manifests/deepcopy stayed stale relative to the type
   changes, OR a generated file (e.g. under `bundle/manifests/`,
   `deploy/crds/`, `zz_generated.deepcopy.go`) was hand-edited directly
   instead of being regenerated via `make generate`/`make manifests`.
4. If the phase touched nothing generated-code-related: this judge is
   **N/A** for that phase — same exclusion-from-mean handling as CG-05, do
   not force a score.

### Scoring (1-5, only when applicable)

- **5**: Correct order followed — generate/manifests ran and passed before
  dependent tests.
- **3**: Order was technically correct but required a re-run/fix (caught
  during the phase's own refinement passes rather than being right the
  first time) — still ended up correct, so not a full violation, but not a
  clean pass either.
- **1**: Tests ran against stale generated code, or a generated file was
  hand-edited instead of regenerated.

---

## Result recording

All 4 judges are written into the same phase-level result file as
`solution_correctness`/`code_quality` — see
[SOLVE_PIPELINE_KPI_EVAL_PROMPT.md](SOLVE_PIPELINE_KPI_EVAL_PROMPT.md) Step C7
for the full `solve-kpi-phase-<N>.yaml` schema including these fields.
