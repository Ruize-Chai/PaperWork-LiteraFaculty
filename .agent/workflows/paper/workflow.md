# Paper workflow

Use this workflow for substantive manuscript drafting, revision, restructuring, figure integration, results updates, citations, review responses, and submission preparation. The shared lifecycle hook classifies requests and initializes context; this workflow governs the actual scientific work.

## Initialize and classify

1. Classify with `paper workflow classify "<request>"`.
2. For a substantial task, run `paper workflow initialize --root . --prompt "<request>"` and inspect only the discovered, relevant sources. Unknown fields are unknown; do not infer a manuscript version, venue, experiment state, or resolution status.
3. Locate the manuscript source and inspect the target section, its surrounding sections, and relevant project status, experiment/evidence records, bibliography, figures, supplement, and review files. Avoid loading unrelated repository contents.
4. Before substantial drafting or restructuring, create a `PaperPlan` with `paper workflow plan "<request>"`. Review target sections, scientific message, claim/evidence IDs, figures, citations, and unresolved risks; correct the plan if the prompt asks for a narrower scope.
5. Trivial sentence and grammar fixes can skip repository-wide initialization and the plan.

## Claim and evidence policy

Use the Paper IR claim registry when present. Map `SUPPORTED` to supported; `PARTIAL` and `CONTESTED` to conditional/open; `PROPOSED` to speculative; `REJECTED` and `SUPERSEDED` to rejected or superseded. A supported claim needs linked evidence and a completed scientific review. Preserve conditions, limitations, scope, and uncertainty. Do not promote a claim because wording was strengthened or a reviewer response was drafted.

When editing a project without Paper IR, keep a small claim-to-evidence mapping in the plan or revision notes. Link IDs or source paths for theory, experiments, figures, and tables. Do not create a heavyweight registry solely to make a trivial edit.

## Figure and citation routing

For figure work, initialize `PaperContext`, inspect the existing figure and its claim, and follow the repository figure workflow if present. Build a figure plan, select a backend deliberately, render, visually inspect the output, then update the manuscript. Retain provenance and note whether an asset is exploratory or final. The paper initializer lists known assets and does not regenerate them.

For citation work, detect the bibliography/citation system and inspect existing entries first. Reuse verified entries where appropriate. Keep missing or uncertain citations explicit; never invent bibliographic metadata. Separate background citations from evidence for the paper's own results. Use the project's literature-search workflow when available.

For referee responses, inspect the reports and existing response letter before editing. Track each point as unresolved, partially resolved, resolved with evidence, author disagreement, or requiring new validation. A prose rewrite alone does not resolve a scientific concern.

## Write and audit

Run `paper workflow prewrite "<request>"` before substantial changes. After writing, run `paper workflow postwrite --root . --path <changed-file>` and, when Paper IR exists, `paper --ir <path> audit`. Treat checks as prompts for review, not proof of scientific correctness.

Check for claims stronger than evidence; inconsistencies across abstract, body, conclusion, and response letter; stale values and experiment names; removed caveats; incorrect section/figure/table/appendix numbering; missing or unused citation keys; unresolved placeholders; stale captions; missing assets; and mismatched manuscript, project, experiment, and review versions. Verify that each figure/caption supports only its linked claim. Record any unresolved issue instead of silently resolving it.

## Workflow stages

Run only the applicable stages: discovery → scientific state → plan → draft/revision → figure/table integration → citation pass → scientific audit → language/presentation pass → submission checks. The hook layer routes and initializes; it does not draft text.
