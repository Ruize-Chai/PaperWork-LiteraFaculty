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

The miniature example includes input artifacts, a derivation, a numerical sweep, evidence and claims, equation and figure bindings, a manuscript, an unresolved citation requirement, and dependency edges. `paper_with_error.json` is a negative fixture with a missing figure reference; `paper audit` reports it.

## Current scope

Implemented: Paper IR v0.1 schema and validation, evidence/claim references, source provenance, dependency traversal and invalidation reports, compact warmup, deterministic reference audit, a narrow deterministic language cleanup with locked-token guard, Markdown and basic LaTeX compilation, CLI, example, and tests.

Not yet implemented: source importers, DOI retrieval/verification, citation formatting, provider-backed prose drafting/refinement, semantic entailment checking, richer numeric/equation/figure audits, reviewer simulation and revisions, incremental artifact cache, venue adapters, and submission bundles. The language rewriter uses one safe phrase substitution and is not a general-purpose language refiner. The LaTeX backend emits a portable generic skeleton and does not invoke a TeX engine.

See [Paper IR constraints](PAPER_IR_CONSTRAINTS.md), [architecture](docs/architecture.md), and the [reuse survey](docs/reuse_survey.md).
