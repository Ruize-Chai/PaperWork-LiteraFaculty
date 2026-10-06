# Repository agent instructions

Before editing, inspect the repository status, relevant source files, tests, and examples. Read `PIPELINE_MENU.yaml` and inspect `.agent/skills/` before using or proposing workflow functionality.

For substantive manuscript or scientific-writing work, begin with `paper initialize` and inspect its `workflow_session.json` output before planning or drafting. Follow the applicable operational entry point in `.agent/skills/` and the detailed workflow in `.agent/workflows/paper/workflow.md`.

Treat Paper IR as the canonical structured source of truth. Markdown and LaTeX are compiled views. Reuse the existing `paper` commands and modules before writing ad hoc replacements. Do not bypass claim IDs, evidence links, provenance, dependency edges, or explicit unresolved states. Changes to upstream evidence require dependency invalidation review.

Language cleanup must use the guarded refinement path and preserve meaning-lock tokens; do not change scientific meaning, claim strength, or caveats as part of a language-only edit. Keep LLM-authored prose noncanonical until it is deliberately reviewed and represented in the manuscript workflow.

Before declaring a manuscript task complete, run the applicable IR validation, cross-reference audit, language meaning-lock check when prose changed, compile smoke test when manuscript output changed, and dependency invalidation review when upstream evidence changed. The handoff must state which gates actually passed; a successful file write alone is not scientific completion.

Preserve compatibility with the checked-in examples and tests. Prefer established scholarly components for mature citation, DOI, review, venue, or submission functions rather than rebuilding them without a clear need. Keep deterministic core behavior provider-independent and report unsupported or planned capabilities as such.
