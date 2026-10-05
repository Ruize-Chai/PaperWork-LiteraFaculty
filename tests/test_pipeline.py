import json
import tempfile
import unittest
from pathlib import Path

from paper_pipeline.audit import audit, invalidation_report
from paper_pipeline.compiler import compile_latex, compile_markdown
from paper_pipeline.ir import ValidationError, load_ir, validate_ir
from paper_pipeline.language import check_refinement, refine_text

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.ir = load_ir(ROOT / "examples/miniature/paper.json")

    def test_example_ir_valid_and_audits_clean(self):
        validate_ir(self.ir)
        self.assertEqual(audit(self.ir), [])

    def test_detects_unknown_figure_reference(self):
        data = json.loads((ROOT / "examples/miniature/paper_with_error.json").read_text())
        issues = audit(data)
        self.assertTrue(any("unknown figure reference FIG_MISSING" in issue for issue in issues))
        self.assertTrue(any("unknown object FIG_MISSING" in issue for issue in issues))

    def test_invalid_status_rejected(self):
        data = json.loads(json.dumps(self.ir))
        data["claims"][0]["status"] = "CERTAIN"
        with self.assertRaises(ValidationError):
            validate_ir(data)

    def test_dependency_invalidation_is_transitive_and_stable(self):
        report = invalidation_report(self.ir, ["EXP_STEP_SWEEP"])
        self.assertEqual(report["invalidated"], ["C_QUADRATIC", "FIG_ERROR", "SEC_ABSTRACT", "SEC_RESULTS"])

    def test_language_guard_preserves_values_symbols_and_locked_sentence(self):
        original = r"We find 0.5004 with \epsilon and call this result C_ENDPOINT."
        revised = r"We find 0.5004 using \epsilon and call this result C_ENDPOINT."
        self.assertEqual(check_refinement(original, revised, ["We find 0.5004 using \\epsilon and call this result C_ENDPOINT."]), [])
        self.assertTrue(check_refinement(original, revised.replace("0.5004", "0.51")))
        self.assertTrue(check_refinement("The result may hold.", "The result demonstrates.") )
        original = r"In order to estimate 0.5004, we use \epsilon."
        refined = refine_text(original)
        self.assertEqual(refined, r"To estimate 0.5004, we use \epsilon.")
        self.assertEqual(check_refinement(original, refined), [])

    def test_compilers_emit_manuscript_structure(self):
        self.assertIn("# A toy convergence result", compile_markdown(self.ir))
        latex = compile_latex(self.ir)
        self.assertIn(r"\documentclass{article}", latex)
        self.assertIn(r"\section{Results}", latex)


if __name__ == "__main__":
    unittest.main()
