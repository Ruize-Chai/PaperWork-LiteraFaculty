# Architecture decisions

## 2026-10-06: small offline-first MVP

The provided directory had no source tree or Git metadata. The implementation is therefore a fresh MVP in the supplied folder, not an extension of existing modules. GitHub was not reachable from the runtime, so repository history and its conventions could not be inspected.

The blueprint calls for a staged pipeline. The first cycle implements the stable center: JSON Paper IR, provenance-bearing evidence, explicit claims, reference validation, downstream dependency traversal, minimal compilers, a narrow language safety guard, and a CLI. It does not claim production readiness.

Reuse survey results are in [reuse_survey.md](reuse_survey.md). Chosen v0.1 dependencies are Python's standard library only. Pandoc/citeproc, scholarly APIs, Pydantic, and venue templates remain optional follow-on integrations to avoid duplicating mature infrastructure or adding an unverified runtime dependency to the smallest runnable core.
