"""Hybrid deterministic + LLM report generation.

- ``implementation-report.md`` and ``deviation-observed.md`` are fully
  deterministic — built directly from files already on disk
  (``implementation/task-reports/*.md``). No LLM call needed.
- ``<artifact>_evaluation_report.md`` mixes a deterministic scorecard table
  (from ``eval-results/*.yaml``) with one short LLM call for the prose Gap
  Analysis / Quality Assessment / Recommendations narrative
  (STAGE_EVAL_GATE_PROMPT.md Step 4 report structure).

Invoked as:
    python -m openspec.llm_gen.run --stage report --change "<name>" --report-id implementation-report
    python -m openspec.llm_gen.run --stage report --change "<name>" --report-id deviation-observed
    python -m openspec.llm_gen.run --stage report --change "<name>" --report-id evaluation-report --artifact-id plan
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from openspec.llm_gen import context_pack as ctx
from openspec.llm_gen.config import load_llm_config
from openspec.llm_gen.provider import LLMError, get_provider

_NARRATIVE_SYSTEM_PROMPT = """You write the narrative sections of an OpenSpec evaluation report:
Gap Analysis, Quality Assessment, and Recommendations. You are given the artifact, its eval
scorecard (if any), and its declared dependency artifacts. Do not repeat the scorecard table
verbatim. Cite specific missing or inconsistent content with a severity: CRITICAL / MODERATE / MINOR.

Output ONLY markdown for these three sections, in this exact order and with these exact headings,
no other headings, no preamble, no code fences:

## Gap Analysis

## Quality Assessment

## Recommendations
"""


def _read_eval_results(cdir: Path, artifact_id: str) -> dict[str, Any]:
    path = cdir / "eval-results" / f"{artifact_id}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _scorecard_table(eval_data: dict[str, Any]) -> str:
    if not eval_data:
        return "_No stage eval file for this artifact — rubric/skip gate, no case scoring._"
    cases = eval_data.get("cases", [])
    passed = sum(1 for c in cases if c.get("pass"))
    header = (
        "| Metric | Value |\n|--------|-------|\n"
        f"| Overall score | {eval_data.get('overall_score', 0)}% |\n"
        f"| Cases passed | {passed} / {len(cases)} |\n"
        f"| Cases failed | {len(cases) - passed} |\n"
        f"| Refinement applied | {'Yes' if eval_data.get('refinement_round', 1) > 1 else 'No'} |\n\n"
        "### Cases Detail\n\n| Case ID | Score | Pass | Failures |\n|---------|-------|------|----------|\n"
    )
    rows = "\n".join(
        f"| {c.get('id', '')} | {c.get('score', '')} | {'yes' if c.get('pass') else 'no'} | "
        f"{'; '.join(c.get('failures', []))} |"
        for c in cases
    )
    return header + rows


def run_evaluation_report(change: str, artifact_id: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path(".")
    cdir = ctx.change_dir(change)
    ext = "json" if artifact_id == "validation" else "md"
    artifact_path = cdir / f"{artifact_id}.{ext}"
    output_path = cdir / f"{artifact_id}_evaluation_report.md"

    if not artifact_path.exists():
        return {"ok": False, "reason": f"{artifact_path} not found"}

    eval_data = _read_eval_results(cdir, artifact_id)
    artifact_text = artifact_path.read_text(encoding="utf-8", errors="replace")

    llm_config = load_llm_config(repo_root)
    provider = get_provider(llm_config)

    user = (
        f"artifact_id: {artifact_id}\nartifact_path: {artifact_path}\n\n"
        f"artifact:\n{artifact_text}\n\n"
        f"eval_results (YAML, may be empty if no stage eval file exists):\n{yaml.safe_dump(eval_data) if eval_data else '(none)'}"
    )

    tokens_in, tokens_out = 0, 0
    try:
        resp = provider.complete(system=_NARRATIVE_SYSTEM_PROMPT, user=user, role="judge")
        narrative = resp.text.strip()
        tokens_in, tokens_out = resp.tokens_in, resp.tokens_out
    except LLMError as exc:
        narrative = (
            f"## Gap Analysis\n\n_LLM narrative unavailable: {exc}_\n\n"
            "## Quality Assessment\n\n_Unavailable._\n\n"
            "## Recommendations\n\n_Unavailable._"
        )

    report = (
        f"# Evaluation Report: {artifact_id}\n\n"
        f"**Change:** {change}\n"
        f"**Artifact:** {artifact_id} ({artifact_path})\n"
        f"**Evaluated at:** {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Eval Summary\n\n{_scorecard_table(eval_data)}\n\n"
        f"{narrative}\n"
    )
    output_path.write_text(report, encoding="utf-8")
    return {"ok": True, "artifact": str(output_path), "tokens_in": tokens_in, "tokens_out": tokens_out}


def _task_reports(cdir: Path) -> list[tuple[str, str]]:
    reports_dir = cdir / "implementation" / "task-reports"
    if not reports_dir.exists():
        return []
    return sorted((p.stem, p.read_text(encoding="utf-8", errors="replace")) for p in reports_dir.glob("*.md"))


def run_implementation_report(change: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    del repo_root  # deterministic — no LLM call, no repo_root dependency
    cdir = ctx.change_dir(change)
    output_path = cdir / "implementation-report.md"
    reports = _task_reports(cdir)
    if not reports:
        return {"ok": False, "reason": "no task reports found under implementation/task-reports/"}

    rows = "\n".join(f"| {tid} | implementation/task-reports/{tid}.md |" for tid, _ in reports)
    body = (
        f"# Implementation Report\n\n**Change:** {change}\n"
        f"**Generated at:** {datetime.now(timezone.utc).isoformat()}\n\n"
        "## Summary\n\nAggregated from all approved task reports below.\n\n"
        "## Per-Task Reports\n\n| Task ID | Report |\n|---------|--------|\n" + rows + "\n\n"
        "## All Files Changed\n\nSee individual task reports for files touched per task.\n"
    )
    output_path.write_text(body, encoding="utf-8")
    return {"ok": True, "artifact": str(output_path), "task_count": len(reports)}


def run_deviation_observed(change: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    del repo_root  # deterministic — no LLM call, no repo_root dependency
    cdir = ctx.change_dir(change)
    output_path = cdir / "deviation-observed.md"

    deviations: list[tuple[str, str]] = []
    for tid, text in _task_reports(cdir):
        if "## Deviations" in text:
            section = text.split("## Deviations", 1)[1]
            section = section.split("\n## ", 1)[0]
            if section.strip():
                deviations.append((tid, section.strip()))

    if not deviations:
        return {"ok": True, "skipped": True, "reason": "no task reported deviations — deviation-observed.md not written"}

    body = "# Architectural Decision Records (Deviations)\n\n"
    for tid, section in deviations:
        body += f"## {tid}\n\n{section}\n\n---\n\n"
    output_path.write_text(body.strip() + "\n", encoding="utf-8")
    return {"ok": True, "artifact": str(output_path), "deviation_count": len(deviations)}
