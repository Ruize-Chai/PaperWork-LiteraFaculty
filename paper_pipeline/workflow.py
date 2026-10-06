"""Lightweight manuscript task routing and repository context discovery."""

from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Any

from .audit import audit
from .ir import ValidationError, load_ir

PAPER_OPERATIONS = (
    "draft_new_manuscript", "continue_manuscript", "rewrite_section", "technical_edit",
    "language_edit", "respond_to_referee", "internal_review", "blind_review",
    "citation_work", "figure_integration", "results_update", "submission_preparation",
    "repository_release",
)

_TRIVIAL = re.compile(r"\b(fix this sentence|shorten this paragraph|correct grammar|make this sentence clearer)\b", re.I)
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("respond_to_referee", ("referee", "reviewer report", "response letter", "point-by-point", "reply to reviewers")),
    ("blind_review", ("blind review", "peer review", "review this manuscript", "review the paper")),
    ("submission_preparation", ("submission", "submit the manuscript", "cover letter", "journal formatting", "submission checklist")),
    ("repository_release", ("repository release", "release the paper", "tag and archive", "reproducibility package")),
    ("citation_work", ("citation", "bibliography", "references", "doi", "cite ")),
    ("figure_integration", ("figure", "figures", "caption", "plot", "publication figure")),
    ("internal_review", ("internal review", "audit the manuscript", "check the paper", "scientific review")),
    ("language_edit", ("grammar", "proofread", "copyedit", "language edit", "clearer", "polish the prose")),
    ("technical_edit", ("technical edit", "notation", "equation", "technical correction", "fix the derivation")),
    ("rewrite_section", ("rewrite", "restructure", "rewrite the section", "revise the introduction")),
    ("continue_manuscript", ("continue writing", "continue the manuscript", "continue the paper", "finish the results", "continue writing the results")),
    ("results_update", ("update results", "new results", "results section", "experiment result", "numerical result")),
    ("draft_new_manuscript", ("write the paper", "draft the paper", "write a manuscript", "draft a manuscript", "new manuscript")),
)

_IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", "output"}
_MANUSCRIPT_SUFFIXES = {".tex", ".typ", ".md", ".qmd"}
_SOURCE_HINTS = ("manuscript", "article", "main", "supplement", "response", "rebuttal")


def classify_task(prompt: str) -> dict[str, Any]:
    """Classify a request; short prose fixes deliberately bypass heavy initialization."""
    text = prompt.strip().lower()
    if _TRIVIAL.search(text):
        return {"operation": "language_edit", "paper_related": False, "substantial": False, "reason": "trivial prose edit"}
    for operation, markers in _RULES:
        if any(marker in text for marker in markers):
            return {
                "operation": operation,
                "paper_related": True,
                "substantial": operation not in {"language_edit"},
                "reason": f"matched {operation.replace('_', ' ')} request",
            }
    if re.search(r"\b(paper|manuscript|article|abstract|introduction|results section)\b", text):
        return {"operation": "continue_manuscript", "paper_related": True, "substantial": True, "reason": "manuscript-related request"}
    return {"operation": "other", "paper_related": False, "substantial": False, "reason": "no paper workflow match"}


def _files(root: Path) -> list[Path]:
    out: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        current = Path(directory)
        dirnames[:] = sorted(name for name in dirnames if name not in _IGNORED_DIRS and (not name.startswith(".") or (current == root and name in {".agent", ".codex"})))
        out.extend(current / name for name in filenames)
    return sorted(out, key=lambda path: path.relative_to(root).as_posix())


def _file_refs(files: list[Path], root: Path, predicate, limit: int = 30) -> list[str]:
    return [p.relative_to(root).as_posix() for p in files if predicate(p)][:limit]


def _find_ir(files: list[Path]) -> Path | None:
    candidates = [p for p in files if p.suffix.lower() == ".json" and ("paper-ir" in p.name.lower() or p.name.lower() in {"paper.json", "paper_ir.json"})]
    return sorted(candidates, key=lambda p: ("publication" not in p.parts, len(p.parts), str(p)))[0] if candidates else None


def initialize_paper_context(root: str | Path = ".", prompt: str = "") -> dict[str, Any]:
    """Return concise paths and known state; never infer missing facts."""
    base = Path(root).resolve()
    files = _files(base)
    classification = classify_task(prompt) if prompt else {"operation": "unknown", "paper_related": True, "substantial": False}
    def manuscript_source(path: Path) -> bool:
        relative = path.relative_to(base).as_posix().lower()
        stem = path.stem.lower()
        if path.suffix.lower() not in _MANUSCRIPT_SUFFIXES or relative.startswith("docs/"):
            return False
        if any(word in stem for word in ("paper_ir", "constraints", "audit", "workflow", "report")) or "-build" in stem:
            return False
        return any(h in relative or h in stem for h in _SOURCE_HINTS) or stem == "paper"

    manuscript = _file_refs(files, base, manuscript_source)
    if not manuscript:
        manuscript = _file_refs(files, base, lambda p: p.suffix.lower() in _MANUSCRIPT_SUFFIXES)[:20]
    bibliography = _file_refs(files, base, lambda p: p.suffix.lower() in {".bib", ".bbl", ".ris", ".enl"})
    figures = _file_refs(files, base, lambda p: p.suffix.lower() in {".pdf", ".png", ".svg", ".jpg", ".jpeg", ".eps"} and "figure" in p.as_posix().lower(), limit=15)
    tables = _file_refs(files, base, lambda p: "table" in p.as_posix().lower() and p.suffix.lower() in {".csv", ".tex", ".md", ".json"})
    experiments = _file_refs(files, base, lambda p: any(k in p.as_posix().lower() for k in ("experiment", "results", "sweep", "benchmark", "numerical")) and p.suffix.lower() in {".csv", ".json", ".md", ".ipynb", ".py"})
    reviews = _file_refs(files, base, lambda p: bool(re.search(r"(?:referee|reviewer)[-_ ]?(?:report|comments?)|response[-_ ]letter|rebuttal", p.name, re.I)) and p.suffix.lower() in {".md", ".txt", ".tex", ".docx", ".pdf"})
    status_files = _file_refs(files, base, lambda p: p.name.lower() in {"readme.md", "agents.md", "project_status.md", "status.md", "next_steps.md"})
    ir_path = _find_ir(files)
    context: dict[str, Any] = {
        "project": {"root": str(base), "status_sources": status_files or None},
        "operation": classification["operation"],
        "manuscript": {"paths": manuscript, "version": "unknown", "status": "unknown", "target_venue": "unknown"},
        "scientific_state": {"established_claims": [], "supported_claims": [], "conditional_claims": [], "speculative_claims": [], "open_claims": [], "rejected_claims": [], "open_experiments": [], "claim_evidence": {}},
        "evidence": {"experiments": experiments, "tables": tables, "figures": figures, "supplementary_material": _file_refs(files, base, lambda p: "supplement" in p.as_posix().lower())},
        "review": {"reports": reviews, "unresolved_comments": "unknown"},
        "references": {"bibliography": bibliography, "citation_system": "unknown", "missing_citations": "unknown"},
        "workflow": {"current_stage": "unknown", "applicable_checks": ["scientific consistency", "structure", "citation", "figure", "version"]},
        "output_constraints": "unknown",
        "paper_ir": ir_path.relative_to(base).as_posix() if ir_path else None,
    }
    if ir_path:
        try:
            ir = load_ir(ir_path)
            context["manuscript"].update({
                "version": ir.get("metadata", {}).get("version", ir.get("metadata", {}).get("manuscript_version", "unknown")),
                "status": ir.get("metadata", {}).get("status", "unknown"),
                "target_venue": ir.get("metadata", {}).get("target_venue") or "unknown",
            })
            status_map = {"SUPPORTED": "supported_claims", "PARTIAL": "conditional_claims", "PROPOSED": "speculative_claims", "CONTESTED": "open_claims", "REJECTED": "rejected_claims", "SUPERSEDED": "rejected_claims"}
            for claim in ir.get("claims", []):
                bucket = status_map.get(claim.get("status"), "open_claims")
                context["scientific_state"][bucket].append(claim.get("id"))
                context["scientific_state"]["claim_evidence"][claim.get("id")] = {
                    "status": claim.get("status", "unknown"),
                    "evidence": claim.get("support", {}),
                    "figures": claim.get("figures", []),
                    "citations": claim.get("citations", []),
                }
            context["scientific_state"]["established_claims"] = list(context["scientific_state"]["supported_claims"])
            context["scientific_state"]["open_experiments"] = [
                e.get("id") for e in ir.get("evidence", [])
                if e.get("type") in {"numerical_experiment", "simulation", "benchmark"}
                and str(e.get("status", e.get("result", {}).get("status", ""))).lower() in {"open", "pending", "incomplete", "running"}
            ]
            registered_evidence = [
                {
                    "id": e.get("id"),
                    "type": e.get("type"),
                    "path": e.get("source", {}).get("path", "unknown") if isinstance(e.get("source"), dict) else "unknown",
                    "status": e.get("status", e.get("result", {}).get("status", "unknown")),
                }
                for e in ir.get("evidence", [])
            ]
            context["evidence"]["registered"] = registered_evidence[:30]
            context["evidence"]["experiments"] = sorted(set(context["evidence"]["experiments"] + [e["path"] for e in registered_evidence if e["type"] in {"numerical_experiment", "simulation", "benchmark"} and e["path"] != "unknown"]))[:20]
            claims_for_figure: dict[str, list[str]] = {}
            for claim in ir.get("claims", []):
                for figure_id in claim.get("figures", []):
                    claims_for_figure.setdefault(figure_id, []).append(claim.get("id"))
            context["evidence"]["figure_records"] = [
                {"id": f.get("id"), "path": f.get("path", "unknown"), "status": f.get("status", "unknown"), "claims": claims_for_figure.get(f.get("id"), []), "caption": f.get("caption", "")}
                for f in ir.get("figures", [])
            ][:20]
            context["evidence"]["table_records"] = [
                {"id": t.get("id"), "path": t.get("path", "unknown"), "status": t.get("status", "unknown"), "claims": t.get("claims", [])}
                for t in ir.get("tables", [])
            ][:20]
            context["references"].update({
                "citation_system": "Paper IR citation objects",
                "missing_citations": [c.get("id") for c in ir.get("citations", []) if c.get("verification_status") in {"unresolved", "missing", None} or c.get("doi") is None],
            })
            context["evidence"]["figures"] = sorted(set(context["evidence"]["figures"] + [f.get("path", f.get("id")) for f in ir.get("figures", []) if f.get("path")]))
            context["evidence"]["tables"] = sorted(set(context["evidence"]["tables"] + [t.get("path", t.get("id")) for t in ir.get("tables", []) if t.get("path")]))
            context["workflow"]["current_stage"] = ir.get("metadata", {}).get("workflow_stage", "unknown")
            context["workflow"]["ir_audit_issues"] = audit(ir)
        except ValidationError as exc:
            context["paper_ir_error"] = str(exc).splitlines()[:5]
    if classification["operation"] == "respond_to_referee":
        context["review"]["focus"] = "inspect listed reports and classify each item before editing"
    if classification["operation"] == "figure_integration":
        context["figure_workflow"] = {"existing_figures": context["evidence"]["figures"], "workflow": ".agent/workflows/figure/workflow.md" if (base / ".agent/workflows/figure/workflow.md").exists() else "unknown"}
    context["discovery_limits"] = "paths and compact metadata only; source files were not ingested"
    return context


def make_paper_plan(prompt: str, root: str | Path = ".") -> dict[str, Any]:
    classification = classify_task(prompt)
    context = initialize_paper_context(root, prompt)
    try:
        ir = load_ir(Path(root) / context["paper_ir"]) if context.get("paper_ir") else {}
    except ValidationError:
        ir = {}
    text = prompt.lower()
    ignored = {"continue", "writing", "write", "rewrite", "revise", "section", "paper", "manuscript", "the", "this", "from", "with", "according"}
    prompt_terms = {word.rstrip("s") for word in re.findall(r"[a-z0-9]+", text) if len(word) > 3 and word not in ignored}
    selected_sections = []
    for section in ir.get("sections", []):
        title_terms = {word.rstrip("s") for word in re.findall(r"[a-z0-9]+", section.get("title", "").lower())}
        section_id = section.get("id", "")
        if section_id.lower() in text or prompt_terms.intersection(title_terms):
            selected_sections.append(section)
    section_refs = [section.get("id") for section in selected_sections]
    if not section_refs and classification["operation"] in {"continue_manuscript", "rewrite_section", "results_update"}:
        selected_sections = [s for s in ir.get("sections", []) if s.get("status") in {"pending", "draft", "in_progress"}]
        section_refs = [s.get("id") for s in selected_sections]
    selected_claims = {claim_id for section in selected_sections for claim_id in section.get("claims", [])}
    claims = [c for c in ir.get("claims", []) if not selected_sections or c.get("id") in selected_claims]
    selected_evidence = {evidence_id for section in selected_sections for evidence_id in section.get("evidence", [])}
    evidence = [e for e in ir.get("evidence", []) if not selected_sections or e.get("id") in selected_evidence]
    claim_figures = {figure_id for claim in claims for figure_id in claim.get("figures", [])}
    selected_figures = [f for f in ir.get("figures", []) if not selected_sections or f.get("id") in claim_figures or f.get("evidence") and any(e in selected_evidence for e in f.get("evidence", []))]
    selected_tables = [t for t in ir.get("tables", []) if not selected_sections or t.get("claims") and any(c in selected_claims for c in t.get("claims", []))]
    return {
        "operation": classification["operation"],
        "target_sections": section_refs or "unknown",
        "scientific_message": ir.get("thesis", {}).get("central_result", "unknown"),
        "claims_used": [c.get("id") for c in claims if c.get("status") in {"SUPPORTED", "PARTIAL"}],
        "evidence_used": [e.get("id") for e in evidence],
        "figures_used": [f.get("id") for f in selected_figures],
        "tables_used": [t.get("id") for t in selected_tables],
        "citations_needed": context["references"]["missing_citations"],
        "unresolved_risks": context["scientific_state"]["open_claims"] + context["scientific_state"]["conditional_claims"] + context["scientific_state"]["open_experiments"],
    }


def prewrite_check(prompt: str, root: str | Path = ".") -> dict[str, Any]:
    classification = classify_task(prompt)
    if not classification["paper_related"] or not classification["substantial"]:
        return {"required": False, "operation": classification["operation"], "reason": classification["reason"]}
    context = initialize_paper_context(root, prompt)
    return {
        "required": True,
        "operation": classification["operation"],
        "checks": {
            "workflow_initialized": True,
            "operation_classified": True,
            "scientific_state_inspected": bool(context.get("paper_ir") or context["project"].get("status_sources")),
            "manuscript_version_identified": context["manuscript"]["version"] != "unknown",
            "claim_status_known": bool(context.get("paper_ir")),
            "evidence_located": bool(context["evidence"]["experiments"] or context["evidence"]["figures"] or context["paper_ir"]),
            "review_reports_checked": classification["operation"] != "respond_to_referee" or bool(context["review"]["reports"]),
        },
        "paper_plan_required": classification["substantial"],
        "context": context,
    }


def postwrite_audit(root: str | Path = ".", changed_paths: list[str] | None = None) -> dict[str, Any]:
    base = Path(root).resolve()
    files = _files(base)
    ir_path = _find_ir(files)
    issues: list[str] = []
    if ir_path:
        try:
            issues = audit(load_ir(ir_path))
        except ValidationError as exc:
            issues = [f"Paper IR validation failed: {line}" for line in str(exc).splitlines()[:10]]
    return {
        "changed_paths": changed_paths or [],
        "paper_ir": ir_path.relative_to(base).as_posix() if ir_path else None,
        "scientific_audit_issues": issues if ir_path else "unknown: no Paper IR found",
        "checks": ["claims versus linked evidence", "cross-section consistency", "stale numerical values and experiment names", "caveats retained", "figure assets and captions", "citation keys and placeholders", "numbering and references", "manuscript/project/review version consistency"],
        "note": "Automated structural checks cannot establish scientific truth or reviewer resolution.",
    }
