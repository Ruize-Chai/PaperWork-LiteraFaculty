# Paper IR

Use when registering claims/evidence, changing manuscript structure, or inspecting project state.

Read `PAPER_IR_CONSTRAINTS.md` and `docs/paper_ir.md`; run `paper --ir PATH validate` before relying on an IR. Paper IR JSON is canonical; compiled Markdown/LaTeX are views. Preserve stable IDs, provenance, claim status/strength, evidence-role links, and explicit unresolved metadata. Do not promote claims or fabricate citation/evidence records.

After edits, validate and run `paper --ir PATH audit`. Keep examples compatible and report the exact IR path used.
