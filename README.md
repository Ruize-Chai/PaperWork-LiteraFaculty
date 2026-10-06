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

Start substantive manuscript work with the portable repository initializer. It reads the agent instructions, capability menu, local skills, discovers a Paper IR, runs the existing warmup summary, and writes an ignored session record:

```sh
paper initialize
paper initialize --root . --paper-ir examples/miniature/paper.json
```

Then classify and plan the request before execution:

```sh
paper workflow classify "Write the paper from the current project."
paper workflow initialize --root . --prompt "Write the paper from the current project."
paper workflow plan "Continue writing the Results section." --output /tmp/paper-plan.json
paper workflow prewrite "Revise the manuscript according to the referee report."
paper workflow postwrite --root . --path publication/msf-manuscript.tex --manuscript-output-modified --compile-target latex
paper workflow handoff --root . --plan /tmp/paper-plan.json --manuscript-output-modified --compile-target latex
```

The session JSON lists relevant manuscript/evidence paths, registered claim/evidence state, warmup, available/planned capabilities, skills, and gates. PaperPlan adds affected objects, planned stages, expected outputs, unresolved dependencies, and human-review requirements. Missing values remain `unknown`; discovery does not ingest source files wholesale. For prose changes, pass `--prose-modified --language-original FILE --language-revised FILE` and any repeated `--locked-sentence TEXT`. For upstream evidence changes, pass the changed IDs and acknowledge the review only after inspecting the report with `--invalidation-reviewed`. The handoff remains `pending_human_review` until every listed review requirement is explicitly acknowledged with `--human-review-completed TEXT`. High-level compile and refinement commands warn and continue if no matching `workflow_session.json` exists. The warning is an accidental-bypass guard, not a security boundary.

Local skills are short operational entry points: `initialize`, `paper-ir`, `audit`, `manuscript-build`, `language-refinement`, and `invalidation`. See [`.agent/skills/`](.agent/skills/) and the [workflow plan schema](.agent/workflows/paper/schemas/paper-plan.schema.json).

Repository operations are exposed as compact entry points under [.agent/skills/](.agent/skills/). `PIPELINE_MENU.yaml` distinguishes stable, experimental, planned, and unsupported capabilities. The repository-local Codex hook still provides prompt routing and write reminders; its trust review is runtime-specific, while `paper initialize` remains portable.

The manuscript lifecycle is **INITIALIZE → DISCOVER → PLAN → EXECUTE → AUDIT → HANDOFF**. The handoff reports passed, pending, and failed gates, and never claims that structural checks prove scientific truth. Conditional gates include language meaning-lock when prose changes, compile smoke when output changes, and dependency review when upstream evidence changes.

The miniature example includes input artifacts, a derivation, a numerical sweep, evidence and claims, equation and figure bindings, a manuscript, an unresolved citation requirement, and dependency edges. `paper_with_error.json` is a negative fixture with a missing figure reference; `paper audit` reports it.

## Current scope

Implemented: Paper IR v0.1 schema and validation, evidence/claim references, source provenance, dependency traversal and invalidation reports, compact warmup, deterministic cross-reference audit, a narrow deterministic language cleanup with locked-token guard, Markdown and generic LaTeX source generation, CLI, repository initialization/session state, capability menu, operational local skills, plan/handoff gates, CI, examples, and tests.

Not yet implemented: source importers, DOI retrieval/verification, citation formatting, provider-backed prose drafting/refinement, semantic entailment checking, richer numeric/equation/figure audits, reviewer simulation and revisions, incremental artifact cache, venue adapters, and submission bundles. The paper workflow provides discovery, routing, planning, and deterministic checks; it does not draft text or prove scientific claims. The language rewriter uses one safe phrase substitution and is not a general-purpose language refiner. The LaTeX backend emits a portable generic skeleton and does not invoke a TeX engine.

See [Paper IR constraints](PAPER_IR_CONSTRAINTS.md), [architecture](docs/architecture.md), the [capability menu](PIPELINE_MENU.yaml), and the [reuse survey](docs/reuse_survey.md).
