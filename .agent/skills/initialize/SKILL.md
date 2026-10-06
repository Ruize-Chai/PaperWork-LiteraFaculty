# Initialize manuscript work

Use before substantive manuscript, evidence, review, figure, citation, or submission work.

1. Inspect `AGENTS.md`, `PIPELINE_MENU.yaml`, and applicable `.agent/skills/` entry points.
2. Run `paper initialize` from the repository root. It writes `workflow_session.json` with the selected IR, compact warmup, capabilities, gates, and warnings.
3. Inspect discovered manuscript and evidence paths relevant to the request; do not ingest unrelated files.

Precondition: run from a repository checkout. If no Paper IR is found, initialization still emits a session and reports that state as unknown. Output: `workflow_session.json` (ignored by Git). Continue with plan → execute → audit → handoff; never infer missing project state.
