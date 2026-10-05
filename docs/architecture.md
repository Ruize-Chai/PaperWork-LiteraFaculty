# Architecture

The MVP is a small Python package organized around a versioned JSON intermediate representation. JSON Schema is the cross-language contract; Python's standard library provides runtime parsing and deterministic checks without requiring network access or an install-time dependency. The custom validator covers the constraints used by this CLI; consumers needing full JSON Schema Draft 2020-12 validation may use a compatible validator.

```text
research files → evidence + claims → Paper IR → validation/audit → Markdown or LaTeX
                                          ↘ dependency graph → invalidation report
```

`ir.py` loads and validates. `graph.py` returns transitive descendants in stable breadth-first order. `audit.py` checks support state and selected references. `language.py` protects numeric values, TeX commands, uppercase identifiers, and exact locked sentences during an externally authored refinement. `compiler.py` renders a simple generic manuscript. `cli.py` orchestrates these deterministic stages.

## Decisions

* Use JSON for portable canonical data and publish a JSON Schema; avoid a YAML parser dependency in the first offline MVP.
* Keep validation, graph work, reference checks, and rendering deterministic and provider-independent.
* Do not implement a prose generator. The language helper is a safety gate; semantic equivalence requires human review or a separately qualified semantic checker.
* Keep output compilation separate from the IR. Current generic LaTeX is source output only; a venue adapter and external compiler can be added independently.
* See [architecture decisions](architecture_decisions.md) for reuse and deferred integrations.
