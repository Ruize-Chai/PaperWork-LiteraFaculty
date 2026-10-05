# Evidence model

Evidence is an addressable object with a unique ID, supported type, provenance `source`, and optional `result`, `conditions`, `limitations`, `validation`, and `supports`. Provenance should include enough data to locate/reproduce the artifact and, when available, a repository commit or content hash. Original research files remain untouched; the IR references them.

The evidence registry is currently the `evidence` array in Paper IR. A supported claim references evidence IDs through `support`. Citation requirements use an explicit citation record and must remain marked unresolved until verified. Current CLI checks that claim support references resolve; external fact/DOI verification is deferred.
