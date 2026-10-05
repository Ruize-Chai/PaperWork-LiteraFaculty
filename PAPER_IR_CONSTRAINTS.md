# Paper IR Interoperability Constraints, v0.1

This document defines the stable exchange contract for this implementation. JSON is the canonical serialization. The machine-readable schema is `paper_pipeline/schema/paper-ir-v0.1.schema.json`; the Python validator adds cross-object constraints that JSON Schema alone does not express.

## Required fields

Every document has `paper_ir_version: "0.1"`, `metadata` (object), `claims` (array), `evidence` (array), and `sections` (array). Metadata may contain `title`, `authors`, `target_venue`, and `manuscript_type`. Unknown fields are preserved and permitted for forward-compatible extensions.

Every claim requires a unique non-empty `id`, a `statement` object with at least one non-empty text value, `strength` (`weak`, `moderate`, or `strong`), `status`, and `support`. Status is one of `PROPOSED`, `PARTIAL`, `SUPPORTED`, `CONTESTED`, `REJECTED`, or `SUPERSEDED`. Strength describes rhetorical/evidential ambition; status describes current review state. They are independent.

Every evidence item requires a unique non-empty `id`, supported `type`, and a `source` object. Supported types are `numerical_experiment`, `analytic_derivation`, `theorem`, `proof`, `dataset`, `measurement`, `simulation`, `benchmark`, `literature_result`, `external_fact`, `figure`, `table`, `notebook_output`, and `code_execution`. Source should identify an immutable/versioned artifact where possible: path or URL, repository, commit, command, timestamp, DOI, dataset/version, or equivalent. Do not imply provenance that is not known.

Other object collections are `equations`, `figures`, `tables`, `citations`, `sections`, `limitations`, and `open_questions`. Each object has a globally unique `id`. `dependencies` is an array of directed edges with `source` and `target` IDs, optionally annotated by `relationship`.

## Identity and relationships

IDs are case-sensitive, stable within a document, and globally unique across object collections. Once published or cited externally, do not recycle an ID for a different object. A claim's `support` maps evidence-role names to arrays of evidence IDs. Claims may also carry `figures`, `citations`, `limitations`, and `used_by` references. Sections may carry `claims`, `evidence`, `purpose`/`role`, `status`, and `text`. Citation requirements must remain explicitly unresolved until metadata and relevance are verified; a plausible DOI is not evidence of a real citation.

Dependency edges point upstream-to-downstream: `evidence → claim → figure/section → downstream section`. Descendants of a changed node are stale and must be reviewed or rebuilt. The CLI reports the transitive descendants; it does not mutate records or claim that a rebuild occurred. Cycles should be avoided; consumers may reject cyclic graphs.

## Provenance and status semantics

Evidence provenance is mandatory at the object level (`source` must exist) and should be sufficiently specific to locate or reproduce the source. Generated content should record source IDs, transformation, and generator metadata when it is added by a future writer. Trivial formatting operations need not be separately recorded.

`PROPOSED` is an unverified candidate; `PARTIAL` has some but insufficient support; `SUPPORTED` passed the project's stated evidence review; `CONTESTED` has unresolved contradictory evidence; `REJECTED` was assessed and not accepted; `SUPERSEDED` was replaced by a newer claim. `SUPPORTED` requires linked evidence in a completed scientific audit, even though the structural validator permits policy-specific incomplete states.

## Validation and invalidation

The structural validator checks version, field shapes, globally unique identities, supported claim/evidence enums, evidence source objects, claim-to-evidence references, and dependency endpoints/self-loops. Audit adds unsupported-claim and selected manuscript cross-reference checks. A valid document is structurally coherent; this is not a proof that the science is correct.

When source content changes, the producer should update its source/version/hash metadata and mark dependent descendants stale. Rebuild only affected descendants and preserve unchanged/manual-locked objects. This MVP exposes a deterministic descendant report but does not store hashes, stale states, or rebuild outputs.

## Versioning, extensions, and serialization

The top-level version is a string. Patch-compatible additions may add optional fields while retaining meanings and existing IDs. A breaking rename, changed status meaning, or changed reference semantics requires a new minor schema version and migration guidance; consumers must reject unknown major contracts rather than silently reinterpret them. Unknown fields are allowed and should be round-tripped by consumers where feasible.

Serialize as UTF-8 JSON, preserve Unicode, use arrays for ordered content, and use ISO-8601 UTC timestamps when timestamps are added. JSON object-key order is not semantically significant. Numeric scientific values should remain JSON numbers unless exact decimal/uncertainty semantics require strings or a structured quantity object; units and conditions must accompany values.

## Proposed v0.2 changes

Add explicit schema-level object discriminators and per-type definitions; first-class provenance records with content hashes; typed support edges and citation requirements; source spans and human-lock metadata; a formal stale/invalidated state; structured quantities with units and uncertainty; relationship validation across every collection; and migration tooling. These changes are proposals, not v0.1 requirements.
