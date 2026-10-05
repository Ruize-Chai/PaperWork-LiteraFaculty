"""Dependency graph operations for invalidating only downstream IR objects."""

from collections import defaultdict, deque
from typing import Any


def dependents(ir: dict[str, Any], changed_ids: list[str]) -> list[str]:
    """Return transitive descendants in stable breadth-first order."""
    edges: dict[str, list[str]] = defaultdict(list)
    for edge in ir.get("dependencies", []):
        edges[edge["source"]].append(edge["target"])
    seen = set(changed_ids)
    result: list[str] = []
    queue = deque(changed_ids)
    while queue:
        current = queue.popleft()
        for child in sorted(edges[current]):
            if child not in seen:
                seen.add(child)
                result.append(child)
                queue.append(child)
    return result

