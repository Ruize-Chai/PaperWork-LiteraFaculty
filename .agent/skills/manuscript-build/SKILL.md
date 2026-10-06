# Manuscript build

Use to produce Markdown or generic LaTeX views from a validated Paper IR.

Preconditions: initialize substantive work; validate the selected IR. Use `paper --ir PATH compile --target markdown|latex --output OUT`. The output is generated view text, not canonical manuscript state; current LaTeX generation does not run TeX.

After modifying manuscript output, run a compile smoke check from the IR, inspect references and included assets, and report the exact backend and checks passed.
