import json
import runpy
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from paper_pipeline.audit import audit, invalidation_report
from paper_pipeline.compiler import compile_latex, compile_markdown
from paper_pipeline.ir import ValidationError, load_ir, validate_ir
from paper_pipeline.language import check_refinement, refine_text
from paper_pipeline.workflow import (
    build_handoff,
    build_workflow_session,
    classify_task,
    initialize_paper_context,
    make_paper_plan,
    postwrite_audit,
    prewrite_check,
    workflow_initialized,
    write_workflow_session,
    _menu_capabilities,
)
from paper_pipeline.cli import main as cli_main

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

    def test_paper_task_classifier_separates_workflow_operations(self):
        cases = {
            "Write the paper from the current project.": "draft_new_manuscript",
            "Continue writing the Results section.": "continue_manuscript",
            "Rewrite the introduction section.": "rewrite_section",
            "Make a technical correction to the equation.": "technical_edit",
            "Proofread the abstract for grammar.": "language_edit",
            "Revise the manuscript according to the referee report.": "respond_to_referee",
            "Run an internal review of the manuscript.": "internal_review",
            "Please blind review this paper.": "blind_review",
            "Check the bibliography citations.": "citation_work",
            "Improve Figure 3 and its caption.": "figure_integration",
            "Update results with the new experiment result.": "results_update",
            "Prepare the submission checklist.": "submission_preparation",
            "Prepare the reproducibility package release.": "repository_release",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_task(prompt)["operation"], expected)

    def test_paper_context_and_plan_use_ir_without_ingesting_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "paper.json").write_text((ROOT / "examples/miniature/paper.json").read_text(), encoding="utf-8")
            context = initialize_paper_context(root, "Write the paper from the current project.")
            self.assertEqual(context["paper_ir"], "paper.json")
            self.assertIn("C_QUADRATIC", context["scientific_state"]["supported_claims"])
            self.assertIn("REF_QUADRATURE", context["references"]["missing_citations"])
            self.assertEqual(context["manuscript"]["version"], "unknown")
            self.assertEqual(context["evidence"]["figure_records"][0]["claims"], ["C_QUADRATIC"])
            self.assertEqual(context["scientific_state"]["claim_evidence"]["C_QUADRATIC"]["status"], "SUPPORTED")
            self.assertIn("not ingested", context["discovery_limits"])
            plan = make_paper_plan("Continue writing the Results section.", root)
        self.assertEqual(plan["operation"], "continue_manuscript")
        self.assertIn("SEC_RESULTS", plan["target_sections"])
        self.assertIn("C_QUADRATIC", plan["claims_used"])
        self.assertEqual(plan["planned_stages"], ["INITIALIZE", "DISCOVER", "PLAN", "EXECUTE", "AUDIT", "HANDOFF"])
        self.assertIn("paper-ir-validation", plan["required_validation_gates"][0])

    def test_prewrite_guard_skips_trivial_edits_but_requires_plan_for_drafting(self):
        self.assertFalse(prewrite_check("Make this sentence clearer.", ROOT)["required"])
        result = prewrite_check("Write the paper from the current project.", ROOT)
        self.assertTrue(result["required"])
        self.assertTrue(result["paper_plan_required"])
        self.assertTrue(result["checks"]["claim_status_known"])

    def test_reviewer_and_figure_discovery_are_included_in_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manuscript").mkdir()
            (root / "manuscript" / "main.tex").write_text("\\section{Results}", encoding="utf-8")
            (root / "manuscript" / "refs.bib").write_text("", encoding="utf-8")
            (root / "reviews").mkdir()
            (root / "reviews" / "referee_report_R1.md").write_text("Concern", encoding="utf-8")
            (root / "figures").mkdir()
            (root / "figures" / "figure-3.pdf").write_bytes(b"pdf")
            review = initialize_paper_context(root, "Revise according to the referee report.")
            self.assertEqual(review["operation"], "respond_to_referee")
            self.assertIn("reviews/referee_report_R1.md", review["review"]["reports"])
            figure = initialize_paper_context(root, "Replace Figure 3 with a publication figure.")
            self.assertEqual(figure["operation"], "figure_integration")
            self.assertIn("figures/figure-3.pdf", figure["evidence"]["figures"])
            self.assertEqual(figure["figure_workflow"]["workflow"], "unknown")

    def test_shared_hook_routes_prompts_and_runs_write_checks(self):
        handle = runpy.run_path(str(ROOT / ".codex/hooks/workflow.py"))["handle"]
        prompt = handle({"hook_event_name": "UserPromptSubmit", "cwd": str(ROOT), "prompt": "Write the paper from the current project."})
        self.assertIn("Paper workflow initialized", prompt["hookSpecificOutput"]["additionalContext"])
        trivial = handle({"hook_event_name": "UserPromptSubmit", "cwd": str(ROOT), "prompt": "Make this sentence clearer."})
        self.assertIsNone(trivial)
        large_change = "text " * 150
        before = handle({"hook_event_name": "PreToolUse", "cwd": str(ROOT), "tool_input": {"file_path": "publication/msf-manuscript.tex", "content": large_change}})
        self.assertIn("Pre-write guard", before["hookSpecificOutput"]["additionalContext"])
        after = handle({"hook_event_name": "PostToolUse", "cwd": str(ROOT), "tool_input": {"file_path": "publication/msf-manuscript.tex", "content": large_change}})
        self.assertIn("Post-write audit", after["hookSpecificOutput"]["additionalContext"])

    def test_initialize_writes_compact_portable_workflow_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("repository instructions", encoding="utf-8")
            (root / "PIPELINE_MENU.yaml").write_text(
                "capabilities:\n  - id: paper-ir-validation\n    status: stable\n    stability: deterministic-core\n    entrypoint: \"paper validate\"\n    required_gates: []\nplanned_capabilities: []\n",
                encoding="utf-8",
            )
            skill = root / ".agent/skills/initialize/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("initialize", encoding="utf-8")
            (root / "paper.json").write_text((ROOT / "examples/miniature/paper.json").read_text(), encoding="utf-8")
            session = build_workflow_session(root)
            self.assertTrue(session["initialized"])
            self.assertEqual(session["paper_ir_version"], "0.1")
            self.assertIn("paper-ir-validation", [item["id"] for item in session["available_capabilities"]])
            self.assertEqual(session["planned_capabilities"], [])
            self.assertTrue(session["initialization_inputs"]["agent_instructions_loaded"])
            self.assertIn(".agent/skills/initialize/SKILL.md", session["initialization_inputs"]["skills"])
            self.assertEqual(session["project_state"]["paper_context"]["paper_ir"], "paper.json")
            output, written = write_workflow_session(root)
            self.assertTrue(output.exists())
            self.assertTrue(workflow_initialized(root))
            self.assertEqual(json.loads(output.read_text()), written)
            with (root / "paper.json").open("a", encoding="utf-8") as source:
                source.write("\n")
            self.assertFalse(workflow_initialized(root, "paper.json"))

    def test_capability_menu_separates_available_and_planned_work(self):
        capabilities, planned, gates = _menu_capabilities((ROOT / "PIPELINE_MENU.yaml").read_text(encoding="utf-8"))
        self.assertTrue(capabilities)
        self.assertTrue(planned)
        self.assertTrue(all(item["status"] == "planned" for item in planned))
        self.assertIn("paper-ir-validation", [item["id"] for item in capabilities])
        self.assertIn("human-review", gates)

    def test_execution_without_initialize_warns_but_continues(self):
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "compiled.md"
            stderr = StringIO()
            os.chdir(root)
            try:
                with redirect_stderr(stderr):
                    status = cli_main(["--ir", str(ROOT / "examples/miniature/paper.json"), "compile", "--target", "markdown", "--output", str(target)])
            finally:
                os.chdir(old_cwd)
            self.assertEqual(status, 0)
            self.assertTrue(target.is_file())
            self.assertIn("workflow is not initialized", stderr.getvalue())
            self.assertFalse(workflow_initialized(root))

    def test_handoff_reports_only_gates_that_actually_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "paper.json").write_text((ROOT / "examples/miniature/paper.json").read_text(), encoding="utf-8")
            report = postwrite_audit(
                root,
                prose_modified=True,
                language_original="The value may equal 2.",
                language_revised="The value equals 2.",
                manuscript_output_modified=True,
                compile_target="markdown",
                upstream_evidence_changed=["EXP_STEP_SWEEP"],
            )
            self.assertEqual(report["gates"]["paper-ir-validation"]["status"], "passed")
            self.assertEqual(report["gates"]["language-meaning-lock"]["status"], "failed")
            self.assertEqual(report["gates"]["compile-smoke"]["status"], "passed")
            self.assertEqual(report["gates"]["dependency-invalidation-review"]["status"], "pending_human_review")
            plan = make_paper_plan("Rewrite the Results section.", root)
            handoff = build_handoff(plan, report)
            self.assertEqual(handoff["completion_status"], "failed")
            self.assertFalse(handoff["scientific_claims_verified"])
            passing = postwrite_audit(
                root,
                prose_modified=True,
                language_original="The value may equal 2.",
                language_revised="The value may equal 2.",
                manuscript_output_modified=True,
                compile_target="latex",
                upstream_evidence_changed=["EXP_STEP_SWEEP"],
                invalidation_reviewed=True,
            )
            self.assertEqual(passing["quality_gate_status"], "passed")
            self.assertEqual(len(passing["passed_gates"]), 5)
            pending = build_handoff(plan, passing)
            self.assertEqual(pending["completion_status"], "pending_human_review")
            completed = build_handoff(plan, passing, plan["human_review_requirements"])
            self.assertEqual(completed["completion_status"], "complete")
            self.assertEqual(completed["scientific_completion"], "not_established_by_automated_workflow")


if __name__ == "__main__":
    unittest.main()
