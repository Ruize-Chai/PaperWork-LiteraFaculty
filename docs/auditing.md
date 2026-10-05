# Auditing

`paper validate` checks required top-level data, collection shapes, unique IDs, status/type enums, source presence, claim-to-evidence links, and dependency endpoints. `paper audit` checks that supported claims have evidence, claim figure IDs resolve, section claim/evidence IDs resolve, and `[[ID]]` references in prose resolve.

The negative fixture intentionally contains an unknown figure. Run:

```sh
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper_with_error.json audit
```

The command exits nonzero and names the missing reference. Numeric, equation, notation, citation DOI, figure freshness, and semantic entailment checks remain future work; a clean audit is only as strong as the checks implemented.
