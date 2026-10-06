# PaperWork LiteraFaculty

A small, offline-first scientific manuscript pipeline built around a versioned Paper IR. The IR is the source of truth; compiled Markdown and LaTeX are outputs. The current MVP emphasizes claim/evidence traceability, provenance, deterministic checks, and dependency-aware invalidation.

## Quick start

Python 3.11+ is the only runtime requirement.

```sh
python -m unittest discover -s tests -v
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json validate
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json audit
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json warmup
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json invalidate EXP_STEP_SWEEP
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json refine-language --section SEC_RESULTS --output /tmp/paper-refined.json
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json compile --target latex --output /tmp/paper.tex
```

Install locally to use the `paper` command:

```sh
python -m pip install -e .
paper --ir examples/miniature/paper.json status
```

## Paper workflow initialization

Substantive manuscript requests should start with the workflow router so existing sources and scientific state are discovered before drafting:

```sh
paper workflow classify "Write the paper from the current project."
paper workflow initialize --root . --prompt "Write the paper from the current project."
paper workflow plan "Continue writing the Results section."
paper workflow prewrite "Revise the manuscript according to the referee report."
paper workflow postwrite --root . --path publication/msf-manuscript.tex
```

The discovery output lists relevant manuscript, evidence, figures, bibliography, and review paths and uses `unknown` when the repository does not establish a value. It does not load entire source files. The Paper IR registry supplies claim states and evidence links when available. `paper workflow plan` creates a lightweight plan for substantive work; short copy edits stay lightweight. See [the paper workflow](.agent/workflows/paper/workflow.md) and [post-write checks](.agent/workflows/paper/checks.md).

The repository's shared Codex lifecycle hook is configured in `.codex/hooks.json`. It classifies `UserPromptSubmit`, supplies concise context for substantive paper tasks, and adds pre-write/post-write reminders for substantial manuscript writes. Hooks must be reviewed and trusted in Codex before execution.

The miniature example includes input artifacts, a derivation, a numerical sweep, evidence and claims, equation and figure bindings, a manuscript, an unresolved citation requirement, and dependency edges. `paper_with_error.json` is a negative fixture with a missing figure reference; `paper audit` reports it.

## Current scope

Implemented: Paper IR v0.1 schema and validation, evidence/claim references, source provenance, dependency traversal and invalidation reports, compact warmup, deterministic reference audit, a narrow deterministic language cleanup with locked-token guard, Markdown and basic LaTeX compilation, CLI, example, and tests.

Not yet implemented: source importers, DOI retrieval/verification, citation formatting, provider-backed prose drafting/refinement, semantic entailment checking, richer numeric/equation/figure audits, reviewer simulation and revisions, incremental artifact cache, venue adapters, and submission bundles. The paper workflow provides discovery, routing, planning, and deterministic checks; it does not draft text or prove scientific claims. The language rewriter uses one safe phrase substitution and is not a general-purpose language refiner. The LaTeX backend emits a portable generic skeleton and does not invoke a TeX engine.

See [Paper IR constraints](PAPER_IR_CONSTRAINTS.md), [architecture](docs/architecture.md), and the [reuse survey](docs/reuse_survey.md).
