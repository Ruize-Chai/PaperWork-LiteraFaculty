#!/usr/bin/env python3
"""Shared Codex lifecycle hook for repository discovery and paper workflow routing."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _root(event: dict[str, Any]) -> Path:
    cwd = Path(event.get("cwd") or os.getcwd()).resolve()
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=True)
        return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return cwd


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for nested in value.values() for item in _strings(nested)]
    if isinstance(value, list):
        return [item for nested in value for item in _strings(nested)]
    return []


def _manuscript_write(event: dict[str, Any]) -> tuple[bool, list[str]]:
    strings = _strings(event.get("tool_input", {}))
    pattern = re.compile(r"(?:^|[/\\])(?:manuscript|publication|paper|article|supplement)(?:[/\\]|\.|$)|\.(?:tex|typ|qmd)$", re.I)
    targets = [value for value in strings if pattern.search(value)]
    if not targets:
        return False, []
    content_chars = sum(len(value) for value in strings if len(value) > 150)
    if content_chars and content_chars < 280 and len(targets) <= 2:
        return False, targets
    return True, targets


def handle(event: dict[str, Any]) -> dict[str, Any] | None:
    event_name = event.get("hook_event_name", "")
    root = _root(event)
    sys.path.insert(0, str(root))
    from paper_pipeline.workflow import classify_task, initialize_paper_context, postwrite_audit, prewrite_check

    if event_name == "SessionStart":
        message = (
            "Shared paper workflow tools: `paper workflow classify`, `initialize`, `plan`, `prewrite`, and `postwrite`. "
            "Paper and figure tasks route through the repository workflow; it discovers relevant context but does not draft text."
        )
        return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
    if event_name == "UserPromptSubmit":
        prompt = str(event.get("prompt", ""))
        classification = classify_task(prompt)
        if not classification["paper_related"]:
            return None
        if not classification["substantial"]:
            message = "Lightweight prose edit detected; repository-wide PaperContext and PaperPlan are unnecessary."
        else:
            context = initialize_paper_context(root, prompt)
            summary = {key: context[key] for key in ("operation", "manuscript", "scientific_state", "evidence", "review", "references", "workflow")}
            message = "Paper workflow initialized. Inspect this concise context before substantive edits; use `paper workflow plan` for a PaperPlan.\n" + json.dumps(summary, ensure_ascii=False)
        return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
    if event_name == "PreToolUse":
        substantial, paths = _manuscript_write(event)
        if not substantial:
            return None
        report = prewrite_check("Continue writing the manuscript", root)
        report["changed_targets"] = paths[:8]
        message = "Pre-write guard: a substantial manuscript write is pending. Check initialization and PaperPlan before proceeding.\n" + json.dumps(report, ensure_ascii=False)
        return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
    if event_name == "PostToolUse":
        substantial, paths = _manuscript_write(event)
        if not substantial:
            return None
        report = postwrite_audit(root, paths[:8])
        message = "Post-write audit reminders and structural Paper IR results:\n" + json.dumps(report, ensure_ascii=False)
        return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        result = handle(event)
        if result:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:  # Hook failures should surface without making the hook itself destructive.
        print(json.dumps({"systemMessage": f"Paper workflow hook could not initialize: {exc}"}, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
