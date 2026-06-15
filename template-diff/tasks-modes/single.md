# Template diff: `tasks-modes/single.md`

| Side | Path |
|------|------|
| Schema (upstream) | `schemas/openspec-agile-workflow/templates/tasks-modes/single.md` |
| Refined (eval workflow) | `evals/refined-templates/tasks-modes/single.md` |

## Status

**Changed** — +7 / -0 lines (approx.)

## Unified diff

```diff
--- schemas/openspec-agile-workflow/templates/tasks-modes/single.md
+++ evals/refined-templates/tasks-modes/single.md
@@ -11,6 +11,11 @@
   §2 linear order → §1 DAG → §4 payloads (all tasks, brief) → §5 orchestration notes.

 - Verification tasks: pair substantive implementation tasks with test tasks when constitution requires.

   Use actual Makefile targets from repo_assessment (e.g., `make test`, not `make test-unit` unless evidenced).

+- Reconcile features: pair drift-revert, delete-recreate, and idempotent-reconcile tests per plan §6 and

+  `tasks.md` Operand reconcile features section.

+- OLM/bundle changes: pair with N-1 → N upgrade verification task per `tasks.md` OLM section.

+- Documentation: when plan includes docs phase, include Docs_Agent task with placeholder consistency AC.

+- User-defined controllers: include explicit `Watches()` task when plan §6 requires delete-recreate.

 

 ### Output sections — use these EXACT `##` headings in your response

 

@@ -61,3 +66,5 @@
 - [ ] Target file(s) in each payload trace to repo_assessment.md or plan.md (marked PARTIAL if uncertain)

 - [ ] §5 present with Retry Boundaries, Merge Conflict Hotspots, and Open Questions

 - [ ] No truncated mid-task payloads; document ends cleanly after §5

+- [ ] Operand drift/delete scenarios from plan have paired verification tasks with Task IDs in §0

+- [ ] OLM upgrade and docs placeholder tasks present when plan phases require them

```
