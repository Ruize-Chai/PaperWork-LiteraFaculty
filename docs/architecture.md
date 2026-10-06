# Architecture

The MVP is a small Python package organized around a versioned JSON intermediate representation. JSON Schema is the cross-language contract; Python's standard library provides runtime parsing and deterministic checks without requiring network access or an install-time dependency. The custom validator covers the constraints used by this CLI; consumers needing full JSON Schema Draft 2020-12 validation may use a compatible validator.

```text
INITIALIZE → DISCOVER → PLAN → EXECUTE → AUDIT → HANDOFF
                 ↓          ↓              ↓        ↓
             Paper IR   PaperPlan    IR/compiler   gate results
                                      and guarded edit

research files → evidence + claims → Paper IR → validation/audit → Markdown or LaTeX
                                          ↘ dependency graph → invalidation report
```

`ir.py` loads and validates. `graph.py` returns transitive descendants in stable breadth-first order. `audit.py` checks support state and selected references. `language.py` protects numeric values, TeX commands, uppercase identifiers, and exact locked sentences during an externally authored refinement. `compiler.py` renders generic manuscript views. `workflow.py` discovers repository capabilities and assets, creates `workflow_session.json`, assembles a focused PaperPlan, and reports actual gate states for handoff. It records unknown values as unknown and discovers paths/compact metadata rather than ingesting the full repository.

`AGENTS.md` defines the portable agent entry procedure. `PIPELINE_MENU.yaml` is the machine-readable inventory of stable, experimental, planned, and unsupported functionality. `.agent/skills/` provides concise operational entry points; `.agent/workflows/` holds lifecycle procedures. `.codex/hooks.json` provides optional runtime prompt routing, but initialization is available through the provider-independent `paper initialize` CLI and does not depend on hook trust.

Quality-gate states distinguish `passed`, `failed`, `not_run`, `not_applicable`, and `pending_human_review`. IR validation and structural cross-reference audit can run deterministically. Language meaning-lock requires original and revised text. Compile smoke generates Markdown or LaTeX source in memory and does not invoke TeX. Dependency invalidation reports affected descendants; a human acknowledgement is needed before its review gate passes. Handoff reports listed human-review requirements separately and stays pending until they are explicitly acknowledged. Even after all workflow gates pass, automated state reports that scientific completion is not established. None of these gates proves scientific truth.

CI runs unit/control-layer tests, validates and audits the miniature IR, smoke-generates both output formats, and confirms that the negative audit fixture is rejected.

## Decisions

* Use JSON for portable canonical data and publish a JSON Schema; avoid a YAML parser dependency in the first offline MVP.
* Keep validation, graph work, reference checks, and rendering deterministic and provider-independent.
* Do not implement a prose generator. The language helper is a safety gate; semantic equivalence requires human review or a separately qualified semantic checker.
* Keep output compilation separate from the IR. Current generic LaTeX is source output only; a venue adapter and external compiler can be added independently.
* Keep initialization and session state at the repository workflow boundary; low-level IR and compiler functions remain usable without a session file.
* See [architecture decisions](architecture_decisions.md) for reuse and deferred integrations.
