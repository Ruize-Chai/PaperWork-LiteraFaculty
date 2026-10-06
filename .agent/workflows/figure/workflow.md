# Scientific figure workflow

This workflow is shared with manuscript tasks. Figure requests from a paper prompt keep their `PaperContext` and activate this figure flow; the figure flow does not replace manuscript claim/evidence review.

1. Inspect the paper workflow context, figure index or catalog, relevant source data/code, manuscript references, and the existing target figure. Record whether each candidate is exploratory or final and which claim it supports.
2. State the figure requirement and create a concise `FigurePlan`: supported claim, data/source, intended audience, comparison or takeaway, panel layout, output formats, and visual risks.
3. Choose an available backend deliberately based on input format, reproducibility, and final output requirements. Prefer a small reproducible update to an existing final figure when it meets the need; do not regenerate it merely because a manuscript task mentioned it.
4. Render the planned output. Keep source code/data provenance with the asset and update the figure index with path, status, and claim/evidence links.
5. Visually inspect rendered files at publication scale and check labels, units, legend, color contrast, clipping, panel references, and caption accuracy. A successful render alone is not visual QA.
6. Integrate the approved figure into the manuscript, check numbering and references, and run the paper post-write audit. Keep exploratory figures out of final manuscript paths.

When no rendering backend or source data is available, report the missing input in the plan and do not present an unsupported mock as a scientific result.
