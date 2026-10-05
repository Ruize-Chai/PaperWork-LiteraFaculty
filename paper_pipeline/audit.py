"""Deterministic cross-reference and manuscript consistency checks."""

import re
from typing import Any

from .graph import dependents


def audit(ir: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    ids = {o.get("id") for key in ("claims", "evidence", "equations", "figures", "tables", "citations", "sections") for o in ir.get(key, []) if isinstance(o, dict)}
    claim_ids = {o.get("id") for o in ir.get("claims", [])}
    evidence_ids = {o.get("id") for o in ir.get("evidence", [])}
    for claim in ir.get("claims", []):
        if claim.get("status") == "SUPPORTED" and not any(claim.get("support", {}).values()):
            issues.append(f"{claim['id']}: SUPPORTED claim has no linked evidence")
        for fig in claim.get("figures", []):
            if fig not in {o.get("id") for o in ir.get("figures", [])}:
                issues.append(f"{claim['id']}: unknown figure reference {fig}")
    for section in ir.get("sections", []):
        for cid in section.get("claims", []):
            if cid not in claim_ids:
                issues.append(f"{section.get('id')}: unknown claim reference {cid}")
        for eid in section.get("evidence", []):
            if eid not in evidence_ids:
                issues.append(f"{section.get('id')}: unknown evidence reference {eid}")
    for token in re.findall(r"\[\[([A-Za-z0-9_.:-]+)\]\]", "\n".join(s.get("text", "") for s in ir.get("sections", []))):
        if token not in ids:
            issues.append(f"manuscript references unknown object {token}")
    return issues


def invalidation_report(ir: dict[str, Any], changed: list[str]) -> dict[str, list[str]]:
    impacted = dependents(ir, changed)
    return {"changed": changed, "invalidated": impacted}

