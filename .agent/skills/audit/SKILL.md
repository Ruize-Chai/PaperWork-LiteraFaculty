# Scientific and manuscript audit

Use after substantive manuscript or Paper IR changes and before handoff.

Run `paper --ir PATH validate`, `paper --ir PATH audit`, and `paper workflow postwrite --root . --path CHANGED_FILE`. Check returned cross-reference findings and manually review claim strength, evidence, stale values, caveats, figure captions/assets, citation keys, numbering, and version consistency.

Automated checks are structural, not proof of scientific truth. State unknown or unrun checks explicitly; do not report completion based only on successful writes.
