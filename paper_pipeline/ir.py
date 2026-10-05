"""Paper IR loading and deterministic structural validation (standard library only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CLAIM_STATUSES = {"PROPOSED", "PARTIAL", "SUPPORTED", "CONTESTED", "REJECTED", "SUPERSEDED"}
CLAIM_STRENGTHS = {"weak", "moderate", "strong"}
EVIDENCE_TYPES = {
    "numerical_experiment", "analytic_derivation", "theorem", "proof", "dataset",
    "measurement", "simulation", "benchmark", "literature_result", "external_fact",
    "figure", "table", "notebook_output", "code_execution",
}
OBJECT_LISTS = ("claims", "evidence", "equations", "figures", "tables", "citations", "sections", "limitations", "open_questions", "dependencies")


class ValidationError(ValueError):
    """Raised when an IR file violates the v0.1 interoperability constraints."""


def load_ir(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(str(exc)) from exc
    validate_ir(data)
    return data


def validate_ir(data: Any) -> None:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise ValidationError("Paper IR root must be an object")
    if data.get("paper_ir_version") != "0.1":
        errors.append("paper_ir_version must be '0.1'")
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
    elif not isinstance(metadata.get("authors", []), list):
        errors.append("metadata.authors must be an array")
    for required in ("claims", "evidence", "sections"):
        if required not in data:
            errors.append(f"missing required field: {required}")
    for key in OBJECT_LISTS:
        if key in data and not isinstance(data[key], list):
            errors.append(f"{key} must be an array")
    ids: dict[str, dict[str, Any]] = {}
    for collection in ("claims", "evidence", "equations", "figures", "tables", "citations", "sections", "limitations", "open_questions"):
        objects = data.get(collection, [])
        if not isinstance(objects, list):
            continue
        for index, obj in enumerate(objects):
            where = f"{collection}[{index}]"
            if not isinstance(obj, dict):
                errors.append(f"{where} must be an object")
                continue
            ident = obj.get("id")
            if not isinstance(ident, str) or not ident.strip():
                errors.append(f"{where}.id must be a non-empty string")
            elif ident in ids:
                errors.append(f"duplicate object id: {ident}")
            else:
                ids[ident] = obj
            if collection == "claims":
                if obj.get("status") not in CLAIM_STATUSES:
                    errors.append(f"{where}.status must be one of {sorted(CLAIM_STATUSES)}")
                if obj.get("strength") not in CLAIM_STRENGTHS:
                    errors.append(f"{where}.strength must be one of {sorted(CLAIM_STRENGTHS)}")
                statement = obj.get("statement")
                if not isinstance(statement, dict) or not any(isinstance(v, str) and v.strip() for v in statement.values()):
                    errors.append(f"{where}.statement must contain symbolic or semantic text")
            if collection == "evidence":
                if obj.get("type") not in EVIDENCE_TYPES:
                    errors.append(f"{where}.type is not a supported evidence type")
                if not isinstance(obj.get("source"), dict):
                    errors.append(f"{where}.source must record provenance as an object")
    evidence_ids = {o.get("id") for o in data.get("evidence", []) if isinstance(o, dict)}
    claim_ids = {o.get("id") for o in data.get("claims", []) if isinstance(o, dict)}
    for claim in data.get("claims", []):
        if not isinstance(claim, dict):
            continue
        support = claim.get("support", {})
        if not isinstance(support, dict):
            errors.append(f"claim {claim.get('id')}: support must be an object")
            continue
        for kind, refs in support.items():
            if not isinstance(refs, list):
                errors.append(f"claim {claim.get('id')}: support.{kind} must be an array")
            else:
                errors.extend(f"claim {claim.get('id')}: unknown evidence id {ref}" for ref in refs if ref not in evidence_ids)
    for dep in data.get("dependencies", []):
        if not isinstance(dep, dict):
            errors.append("dependencies entries must be objects")
            continue
        source, target = dep.get("source"), dep.get("target")
        if source not in ids:
            errors.append(f"dependency has unknown source id {source}")
        if target not in ids:
            errors.append(f"dependency has unknown target id {target}")
        if source == target:
            errors.append(f"dependency self-loop at {source}")
    if errors:
        raise ValidationError("\n".join(errors))


def to_warmup(data: dict[str, Any]) -> dict[str, Any]:
    """Create a compact, deterministic project handoff from the current IR."""
    claims: dict[str, list[str]] = {status.lower(): [] for status in sorted(CLAIM_STATUSES)}
    for claim in data.get("claims", []):
        claims[claim["status"].lower()].append(claim["id"])
    return {
        "paper_ir_version": data["paper_ir_version"],
        "title": data.get("metadata", {}).get("title"),
        "central_question": data.get("thesis", {}).get("primary_question"),
        "central_result": data.get("thesis", {}).get("central_result"),
        "claims_by_status": claims,
        "open_questions": data.get("open_questions", []),
        "section_state": {s.get("id"): s.get("status", "pending") for s in data.get("sections", []) if isinstance(s, dict)},
        "next_actions": data.get("next_actions", []),
    }
