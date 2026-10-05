# Paper IR

Paper IR is the canonical structured representation, not an export format for generated prose. v0.1 is UTF-8 JSON described by `paper_pipeline/schema/paper-ir-v0.1.schema.json` and constrained in [PAPER_IR_CONSTRAINTS.md](../PAPER_IR_CONSTRAINTS.md). The miniature `examples/miniature/paper.json` demonstrates metadata, thesis, claims, evidence, equations, figures, citations, sections, limitations, questions, dependencies, and next actions.

Claims have a stable ID, statement, independent strength and status, and support references grouped by evidence role. Evidence has a type, source provenance, result, conditions, and limitations. References use IDs; prose may use `[[OBJECT_ID]]` markers for audit-visible links. Unknown fields are allowed for compatible extension. v0.1 JSON is canonical; YAML import/export is deferred to avoid ambiguous coercions and an unnecessary runtime dependency.

Use `paper validate` for structural checks and `paper audit` for selected evidence and manuscript cross-reference checks. Neither establishes mathematical truth or validates external citation accuracy.
