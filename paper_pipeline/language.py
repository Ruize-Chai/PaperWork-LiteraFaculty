"""Meaning-lock utilities for language edits.

This MVP deliberately does not rewrite scientific prose. It guards human- or
provider-authored refinements by requiring protected tokens and exact locked
sentences to survive byte-for-byte.
"""

import re

SEMANTIC_FORCE = {
    "may", "might", "could", "can", "possibly", "approximately", "suggest",
    "indicate", "demonstrate", "prove", "establish", "must", "only", "all", "some",
}


def protected_tokens(text: str) -> set[str]:
    return (set(re.findall(r"(?:\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b|\\[A-Za-z]+|\b[A-Z][A-Z0-9_]{1,}\b)", text))
            | (set(re.findall(r"\b[\w-]+\b", text.lower())) & SEMANTIC_FORCE))


def check_refinement(original: str, revised: str, locked_sentences: list[str] | None = None) -> list[str]:
    issues = [f"protected scientific token changed or removed: {token}" for token in sorted(protected_tokens(original) - protected_tokens(revised))]
    for sentence in locked_sentences or []:
        if sentence not in revised:
            issues.append("locked sentence changed or removed")
    return issues


def refine_text(text: str) -> str:
    """Apply a tiny, auditable concision rule set; never calls a model."""
    def shorter(match: re.Match[str]) -> str:
        phrase = match.group(0)
        return "TO" if phrase.isupper() else ("To" if phrase[0].isupper() else "to")

    revised = re.sub(r"\bin order to\b", shorter, text, flags=re.IGNORECASE)
    issues = check_refinement(text, revised)
    if issues:
        raise ValueError("refinement failed meaning-lock checks: " + "; ".join(issues))
    return revised
