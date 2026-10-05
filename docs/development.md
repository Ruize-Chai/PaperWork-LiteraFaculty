# Development

Requirements: Python 3.11 or newer. The runtime has no third-party dependencies.

```sh
python -m unittest discover -s tests -v
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json validate
PYTHONPATH=. python -m paper_pipeline.cli --ir examples/miniature/paper.json audit
```

Keep computation deterministic and provider-independent where possible. Add focused `unittest` coverage for schema invariants, graph behavior, audits, and compiler output. External adapters must be optional, have documented license/API terms, and preserve offline use of core validation. The checked-in example serves as a small golden fixture; output snapshots can be added when compiler output becomes a compatibility guarantee.
