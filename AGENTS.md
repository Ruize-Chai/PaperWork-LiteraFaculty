# Repository agent guidance

For substantive manuscript, review, citation, result, submission, or figure work, use the shared router and follow [.agent/workflows/paper/workflow.md](.agent/workflows/paper/workflow.md). Run `paper workflow initialize` before drafting, and create a PaperPlan before substantial changes. The lightweight language-edit exception and the post-write checklist are defined in that workflow.

Repository-local lifecycle routing is configured in `.codex/hooks.json`; the hook layer discovers and routes work but does not draft the manuscript. If hooks have not been reviewed or trusted in the current Codex installation, these repository instructions still describe the required workflow.
