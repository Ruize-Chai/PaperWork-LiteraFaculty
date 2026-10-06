"""Lightweight manuscript task routing and repository context discovery."""

from __future__ import annotations

import re
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import audit
from .compiler import compile_latex, compile_markdown
from .ir import ValidationError, load_ir, to_warmup
from .language import check_refinement

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


def _menu_capabilities(menu_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    capabilities: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    required_gates: list[str] = []
    planned_start = menu_text.find("planned_capabilities:")
    blocks = re.finditer(r"(?ms)^  - id: ([a-z0-9-]+)\n(.*?)(?=^  - id: |^planned_capabilities:|\Z)", menu_text)
    for match in blocks:
        block = match.group(2)
        status_match = re.search(r"(?m)^    status: ([a-z]+)$", block)
        stability_match = re.search(r"(?m)^    stability: ([a-z-]+)$", block)
        entrypoint_match = re.search(r"(?m)^    entrypoint: (.+)$", block)
        gates_match = re.search(r"(?m)^    required_gates: \[(.*?)\]$", block)
        capability = {
            "id": match.group(1),
            "status": status_match.group(1) if status_match else "unknown",
            "stability": stability_match.group(1) if stability_match else "unknown",
            "entrypoint": (None if entrypoint_match.group(1).strip() == "null" else entrypoint_match.group(1).strip('"')) if entrypoint_match else "unknown",
        }
        if planned_start >= 0 and match.start() > planned_start:
            planned.append(capability)
        else:
            capabilities.append(capability)
        if gates_match:
            required_gates.extend(g.strip() for g in gates_match.group(1).split(",") if g.strip())
    return capabilities, planned, sorted(set(required_gates))


def build_workflow_session(root: str | Path = ".", ir_path: str | Path | None = None) -> dict[str, Any]:
    """Build portable, machine-readable repository workflow state without external dependencies."""
    base = Path(root).resolve()
    files = _files(base)
    warnings: list[str] = []
    menu_path = base / "PIPELINE_MENU.yaml"
    if menu_path.is_file():
        capabilities, planned_capabilities, menu_gates = _menu_capabilities(menu_path.read_text(encoding="utf-8"))
        if not capabilities:
            warnings.append("PIPELINE_MENU.yaml contains no recognizable capability entries")
    else:
        capabilities, planned_capabilities, menu_gates = [], [], []
        warnings.append("PIPELINE_MENU.yaml is missing")
    skills = [p.relative_to(base).as_posix() for p in files if p.name == "SKILL.md" and ".agent/skills/" in p.as_posix()]
    agent_file = base / "AGENTS.md"
    agent_guidance = agent_file.read_text(encoding="utf-8") if agent_file.is_file() else ""
    if not agent_guidance:
        warnings.append("AGENTS.md is missing or empty")
    selected_ir = (base / Path(ir_path)).resolve() if ir_path and not Path(ir_path).is_absolute() else Path(ir_path).resolve() if ir_path else _find_ir(files)
    warmup: dict[str, Any] | None = None
    project: dict[str, Any] = {"paper_ir": None, "title": "unknown", "claims": 0, "evidence": 0, "sections": 0, "citation_requirements": "unknown"}
    version = "unknown"
    if selected_ir and selected_ir.is_file():
        try:
            ir = load_ir(selected_ir)
            warmup = to_warmup(ir)
            version = ir["paper_ir_version"]
            project = {
                "paper_ir": selected_ir.relative_to(base).as_posix() if selected_ir.is_relative_to(base) else str(selected_ir),
                "title": ir.get("metadata", {}).get("title", "unknown"),
                "manuscript_version": ir.get("metadata", {}).get("version", ir.get("metadata", {}).get("manuscript_version", "unknown")),
                "status": ir.get("metadata", {}).get("status", "unknown"),
                "target_venue": ir.get("metadata", {}).get("target_venue") or "unknown",
                "claims": len(ir.get("claims", [])),
                "evidence": len(ir.get("evidence", [])),
                "sections": len(ir.get("sections", [])),
                "citation_requirements": sum(c.get("verification_status") in {"unresolved", "missing", None} for c in ir.get("citations", [])),
            }
        except (ValidationError, ValueError) as exc:
            warnings.append(f"Paper IR could not be initialized: {exc}")
    else:
        warnings.append("No Paper IR was discovered; scientific project state remains unknown")
    context = initialize_paper_context(base, ir_path=selected_ir)
    return {
        "initialized": True,
        "workflow": "literafaculty",
        "initialized_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(base),
        "initialization_inputs": {
            "agent_instructions": "AGENTS.md",
            "agent_instructions_loaded": bool(agent_guidance),
            "agent_instructions_sha256": hashlib.sha256(agent_guidance.encode("utf-8")).hexdigest() if agent_guidance else None,
            "capability_menu": "PIPELINE_MENU.yaml",
            "skills": skills,
        },
        "paper_ir_version": version,
        "paper_ir_sha256": hashlib.sha256(selected_ir.read_bytes()).hexdigest() if selected_ir and selected_ir.is_file() else None,
        "available_capabilities": capabilities,
        "planned_capabilities": planned_capabilities,
        "required_gates": ["paper-ir-validation", "cross-reference-audit", "language-meaning-lock-if-prose-changed", "compile-smoke-if-output-changed", "dependency-invalidation-review-if-evidence-changed"],
        "capability_gates": menu_gates,
        "project_state": {**project, "warmup": warmup, "paper_context": context},
        "warnings": warnings,
    }


def write_workflow_session(root: str | Path = ".", ir_path: str | Path | None = None, output: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    base = Path(root).resolve()
    session = build_workflow_session(base, ir_path)
    destination = (base / Path(output)).resolve() if output and not Path(output).is_absolute() else Path(output).resolve() if output else base / "workflow_session.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, session


def workflow_initialized(root: str | Path = ".", ir_path: str | Path | None = None) -> bool:
    base = Path(root).resolve()
    state_path = base / "workflow_session.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if state.get("initialized") is not True or state.get("project_root") != str(base):
        return False
    if ir_path:
        requested = Path(ir_path)
        if not requested.is_absolute():
            requested = base / requested
        recorded = state.get("project_state", {}).get("paper_ir")
        if requested.is_file() and recorded:
            recorded_path = Path(recorded)
            if not recorded_path.is_absolute():
                recorded_path = base / recorded_path
            if requested.resolve() != recorded_path.resolve():
                return False
            expected_hash = state.get("paper_ir_sha256")
            if expected_hash and hashlib.sha256(requested.read_bytes()).hexdigest() != expected_hash:
                return False
    return True


def initialize_paper_context(root: str | Path = ".", prompt: str = "", ir_path: str | Path | None = None) -> dict[str, Any]:
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
    ir_path = (base / Path(ir_path)).resolve() if ir_path and not Path(ir_path).is_absolute() else Path(ir_path).resolve() if ir_path else _find_ir(files)
    ir_display = ir_path.relative_to(base).as_posix() if ir_path and ir_path.is_relative_to(base) else str(ir_path) if ir_path else None
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
        "paper_ir": ir_display,
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


def make_paper_plan(prompt: str, root: str | Path = ".", ir_path: str | Path | None = None) -> dict[str, Any]:
    classification = classify_task(prompt)
    context = initialize_paper_context(root, prompt, ir_path)
    try:
        ir = load_ir(context["paper_ir"] if Path(context["paper_ir"]).is_absolute() else Path(root) / context["paper_ir"]) if context.get("paper_ir") else {}
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
    selected_claim_ids = [c.get("id") for c in claims if c.get("status") in {"SUPPORTED", "PARTIAL"}]
    selected_evidence_ids = [e.get("id") for e in evidence]
    selected_figure_ids = [f.get("id") for f in selected_figures]
    selected_table_ids = [t.get("id") for t in selected_tables]
    unresolved_risks = context["scientific_state"]["open_claims"] + context["scientific_state"]["conditional_claims"] + context["scientific_state"]["open_experiments"]
    citation_ids = context["references"]["missing_citations"]
    outputs = {
        "draft_new_manuscript": ["reviewable manuscript draft", "Paper IR updates if claims/evidence/structure changed"],
        "continue_manuscript": ["reviewable target-section revision"],
        "rewrite_section": ["reviewable section revision"],
        "technical_edit": ["reviewed technical correction"],
        "language_edit": ["meaning-locked prose revision"],
        "respond_to_referee": ["point-by-point response state", "manuscript revision if required"],
        "internal_review": ["review findings with evidence and resolution state"],
        "blind_review": ["review findings with evidence and resolution state"],
        "citation_work": ["verified bibliography updates or explicit unresolved citation requirements"],
        "figure_integration": ["figure plan, reviewed asset, and manuscript integration"],
        "results_update": ["updated results with claim/evidence links"],
        "submission_preparation": ["submission readiness report"],
        "repository_release": ["reproducibility/release readiness report"],
    }.get(classification["operation"], ["reviewable workflow result"])
    human_review = ["scientific claim/evidence consistency"]
    if classification["operation"] == "figure_integration":
        human_review.append("visual figure and caption review")
    if classification["operation"] in {"citation_work", "respond_to_referee"}:
        human_review.append("citation metadata or reviewer-resolution review")
    if classification["operation"] == "language_edit":
        human_review.append("semantic equivalence review")
    return {
        "request": prompt,
        "operation": classification["operation"],
        "target_sections": section_refs or "unknown",
        "scientific_message": ir.get("thesis", {}).get("central_result", "unknown"),
        "claims_used": selected_claim_ids,
        "evidence_used": selected_evidence_ids,
        "figures_used": selected_figure_ids,
        "tables_used": selected_table_ids,
        "citations_needed": citation_ids,
        "unresolved_risks": unresolved_risks,
        "affected_paper_ir_objects": {"sections": section_refs, "claims": selected_claim_ids, "evidence": selected_evidence_ids, "figures": selected_figure_ids, "tables": selected_table_ids, "citations": citation_ids},
        "planned_stages": ["INITIALIZE", "DISCOVER", "PLAN", "EXECUTE", "AUDIT", "HANDOFF"],
        "expected_outputs": outputs,
        "required_validation_gates": ["paper-ir-validation", "cross-reference-audit", "language-meaning-lock if prose was modified", "compile-smoke if manuscript output was modified", "dependency-invalidation-review if upstream evidence changed"],
        "unresolved_dependencies": unresolved_risks + (citation_ids if isinstance(citation_ids, list) else []),
        "human_review_requirements": human_review,
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


def postwrite_audit(
    root: str | Path = ".",
    changed_paths: list[str] | None = None,
    *,
    ir_path: str | Path | None = None,
    prose_modified: bool = False,
    language_original: str | None = None,
    language_revised: str | None = None,
    locked_sentences: list[str] | None = None,
    manuscript_output_modified: bool = False,
    compile_target: str | None = None,
    upstream_evidence_changed: list[str] | None = None,
    invalidation_reviewed: bool = False,
) -> dict[str, Any]:
    base = Path(root).resolve()
    files = _files(base)
    ir_path = (base / Path(ir_path)).resolve() if ir_path and not Path(ir_path).is_absolute() else Path(ir_path).resolve() if ir_path else _find_ir(files)
    ir_display = ir_path.relative_to(base).as_posix() if ir_path and ir_path.is_relative_to(base) else str(ir_path) if ir_path else None
    issues: list[str] = []
    ir: dict[str, Any] | None = None
    validation_status = "not_run"
    if ir_path:
        try:
            ir = load_ir(ir_path)
            validation_status = "passed"
            issues = audit(ir)
        except ValidationError as exc:
            validation_status = "failed"
            issues = [f"Paper IR validation failed: {line}" for line in str(exc).splitlines()[:10]]
    gates: dict[str, dict[str, Any]] = {
        "paper-ir-validation": {"status": validation_status, "details": str(ir_path.relative_to(base)) if ir_path else "No Paper IR discovered"},
        "cross-reference-audit": {"status": "not_run" if ir is None else ("passed" if not issues else "failed"), "details": issues},
    }
    required_gates = ["paper-ir-validation", "cross-reference-audit"]
    if prose_modified:
        required_gates.append("language-meaning-lock")
        if language_original is None or language_revised is None:
            gates["language-meaning-lock"] = {"status": "not_run", "details": "Supply both original and revised prose for a meaning-lock comparison"}
        else:
            language_issues = check_refinement(language_original, language_revised, locked_sentences)
            gates["language-meaning-lock"] = {"status": "failed" if language_issues else "passed", "details": language_issues}
    else:
        gates["language-meaning-lock"] = {"status": "not_applicable", "details": "No prose change declared"}
    if manuscript_output_modified:
        required_gates.append("compile-smoke")
        if ir is None or compile_target not in {"markdown", "latex"}:
            gates["compile-smoke"] = {"status": "not_run", "details": "Requires a valid Paper IR and --compile-target markdown|latex"}
        else:
            try:
                compiled = compile_markdown(ir) if compile_target == "markdown" else compile_latex(ir)
                gates["compile-smoke"] = {"status": "passed" if compiled.strip() else "failed", "details": f"Generated non-empty {compile_target} source in memory"}
            except (KeyError, TypeError, ValueError) as exc:
                gates["compile-smoke"] = {"status": "failed", "details": str(exc)}
    else:
        gates["compile-smoke"] = {"status": "not_applicable", "details": "No manuscript output change declared"}
    changed = upstream_evidence_changed or []
    if changed:
        required_gates.append("dependency-invalidation-review")
        from .audit import invalidation_report
        report = invalidation_report(ir or {}, changed)
        gates["dependency-invalidation-review"] = {
            "status": "not_run" if ir is None else ("passed" if invalidation_reviewed else "pending_human_review"),
            "details": "A valid Paper IR is required to inspect dependency impact" if ir is None else report,
        }
    else:
        gates["dependency-invalidation-review"] = {"status": "not_applicable", "details": "No upstream evidence change declared"}
    required_passed = all(gates.get(name, {}).get("status") == "passed" for name in required_gates)
    required_failed = any(gates.get(name, {}).get("status") == "failed" for name in required_gates)
    return {
        "changed_paths": changed_paths or [],
        "paper_ir": ir_display,
        "scientific_audit_issues": issues if ir_path else "unknown: no Paper IR found",
        "gates": gates,
        "required_gates": required_gates,
        "passed_gates": [name for name in required_gates if gates[name]["status"] == "passed"],
        "pending_gates": [name for name in required_gates if gates[name]["status"] in {"not_run", "pending_human_review"}],
        "failed_gates": [name for name in required_gates if gates[name]["status"] == "failed"],
        "quality_gate_status": "passed" if required_passed else ("failed" if required_failed else "pending"),
        "checks": ["claims versus linked evidence", "cross-section consistency", "stale numerical values and experiment names", "caveats retained", "figure assets and captions", "citation keys and placeholders", "numbering and references", "manuscript/project/review version consistency"],
        "note": "Automated structural checks cannot establish scientific truth or reviewer resolution.",
    }


def build_handoff(plan: dict[str, Any], gate_report: dict[str, Any], completed_human_reviews: list[str] | None = None) -> dict[str, Any]:
    """Combine a plan and observed gates without implying scientific verification."""
    completed = set(completed_human_reviews or [])
    human_requirements = plan.get("human_review_requirements", [])
    human_status = {item: "completed" if item in completed else "pending" for item in human_requirements}
    gate_status = gate_report.get("quality_gate_status", "pending")
    if gate_status == "failed":
        overall = "failed"
    elif gate_status != "passed":
        overall = "pending_gates"
    elif any(status == "pending" for status in human_status.values()):
        overall = "pending_human_review"
    else:
        overall = "complete"
    return {
        "workflow": "literafaculty",
        "request": plan.get("request", "unknown"),
        "operation": plan.get("operation", "unknown"),
        "planned_stages": plan.get("planned_stages", []),
        "affected_paper_ir_objects": plan.get("affected_paper_ir_objects", {}),
        "expected_outputs": plan.get("expected_outputs", []),
        "planned_validation_gates": plan.get("required_validation_gates", []),
        "required_gates": gate_report.get("required_gates", []),
        "passed_gates": gate_report.get("passed_gates", []),
        "pending_gates": gate_report.get("pending_gates", []),
        "failed_gates": gate_report.get("failed_gates", []),
        "gates": gate_report.get("gates", {}),
        "quality_gate_status": gate_status,
        "human_review_status": human_status,
        "completion_status": overall,
        "scientific_claims_verified": False,
        "scientific_completion": "not_established_by_automated_workflow",
        "human_review_requirements": plan.get("human_review_requirements", []),
        "unresolved_dependencies": plan.get("unresolved_dependencies", []),
    }
