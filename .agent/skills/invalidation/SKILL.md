# Dependency invalidation

Use when an upstream experiment, derivation, dataset, or evidence object changes.

Validate the IR, then run `paper --ir PATH invalidate OBJECT_ID...`. Review every reported descendant: claims, figures/tables, and manuscript sections may need revalidation or rebuilding. The command reports impact only; it does not mark records stale or rebuild them automatically.

Before handoff, record the invalidation result and which affected objects were reviewed. Never silently reuse downstream figures or prose after evidence changes.
