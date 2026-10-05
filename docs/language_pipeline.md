# Scientific language pipeline

The intended sequence is content draft → meaning lock → refinement → semantic/terminology checks → human acceptance. Scientific facts remain in claims and evidence; language is a compiled view.

This MVP has no generative model adapter. `refine_text` applies one deterministic concision rewrite (`in order to` → `to`) and then checks protected tokens. `check_refinement(original, revised, locked_sentences)` flags removed/changed numeric tokens, TeX commands, uppercase object-like identifiers, semantic-force terms, or exact locked sentences. This is not a proof of semantic equivalence: paraphrases can change meaning while retaining tokens. The CLI writes a new JSON file and asks for diff review; it does not overwrite the input. Review all scientific edits and extend protected terms per project before using an external refiner.
