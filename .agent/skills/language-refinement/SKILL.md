# Guarded language refinement

Use only for prose cleanup that must preserve scientific meaning. Do not use to strengthen claims, change equations/results, remove caveats, or settle reviewer issues.

Run `paper --ir PATH refine-language --section ID --output COPY`. This applies a narrow deterministic rule and checks meaning-lock tokens; it is not general proofreading. Review the output diff, keep the source IR unchanged until accepted, then validate, audit, and perform human semantic review.
