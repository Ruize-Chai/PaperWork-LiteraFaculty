# Claim graph

Claims encode a scientific statement, type, strength, status, evidence support, scope/limitations, and optional figure/citation links. Status values and meanings are defined in [PAPER_IR_CONSTRAINTS.md](../PAPER_IR_CONSTRAINTS.md). Claim strength never substitutes for the amount or quality of evidence.

The dependency graph is directed from upstream objects to downstream artifacts. `paper invalidate EVIDENCE_ID` walks descendants breadth-first and prints a deterministic invalidation report. The MVP does not mutate statuses or regenerate those descendants.
