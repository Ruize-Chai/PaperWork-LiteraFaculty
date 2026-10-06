"""Command line interface for validating, auditing, compiling, and warming up a paper."""

import argparse
import json
import sys
from pathlib import Path

from .audit import audit, invalidation_report
from .compiler import compile_to
from .ir import ValidationError, load_ir, to_warmup
from .language import refine_text
from .workflow import (
    build_handoff,
    classify_task,
    initialize_paper_context,
    make_paper_plan,
    postwrite_audit,
    prewrite_check,
    workflow_initialized,
    write_workflow_session,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paper", description="Paper IR centered research-to-manuscript tools")
    parser.add_argument("--ir", default="paper.json", help="Paper IR JSON path (default: paper.json)")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate", help="validate IR structure and references")
    subs.add_parser("audit", help="run deterministic scientific consistency checks")
    subs.add_parser("status", help="summarize claims, evidence, and sections")
    subs.add_parser("warmup", help="emit a compact project handoff JSON")
    initialize_cmd = subs.add_parser("initialize", help="create portable repository workflow_session.json")
    initialize_cmd.add_argument("--root", default=".", help="repository root (default: current directory)")
    initialize_cmd.add_argument("--ir", "--paper-ir", dest="initialize_ir", help="optional Paper IR path; otherwise discover it")
    initialize_cmd.add_argument("--output", help="session JSON path (default: ROOT/workflow_session.json)")
    workflow = subs.add_parser("workflow", help="paper workflow initialization, routing, and checks")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    classify = workflow_sub.add_parser("classify", help="classify a paper or figure task")
    classify.add_argument("prompt")
    initialize = workflow_sub.add_parser("initialize", help="discover concise manuscript and scientific context")
    initialize.add_argument("--root", default=".", help="repository root (default: current directory)")
    initialize.add_argument("--prompt", default="", help="optional request used to select relevant context")
    plan = workflow_sub.add_parser("plan", help="create a lightweight PaperPlan for substantive work")
    plan.add_argument("prompt")
    plan.add_argument("--root", default=".")
    plan.add_argument("--paper-ir", help="use this Paper IR instead of automatic discovery")
    plan.add_argument("--output", help="write the plan JSON to this path instead of stdout")
    before = workflow_sub.add_parser("prewrite", help="check initialization before a manuscript write")
    before.add_argument("prompt")
    before.add_argument("--root", default=".")
    after = workflow_sub.add_parser("postwrite", help="run post-write manuscript checks")
    after.add_argument("--root", default=".")
    after.add_argument("--paper-ir", help="use this Paper IR instead of automatic discovery")
    after.add_argument("--path", action="append", default=[], help="changed manuscript or figure path")
    _add_gate_arguments(after)
    handoff = workflow_sub.add_parser("handoff", help="combine a PaperPlan with observed completion gates")
    handoff.add_argument("--root", default=".")
    handoff.add_argument("--plan", required=True, help="PaperPlan JSON path")
    handoff.add_argument("--paper-ir", help="use this Paper IR instead of automatic discovery")
    handoff.add_argument("--path", action="append", default=[], help="changed manuscript or figure path")
    handoff.add_argument("--human-review-completed", action="append", default=[], help="exact human-review requirement from the plan that is complete")
    _add_gate_arguments(handoff)
    handoff.add_argument("--output", help="write handoff JSON to this path instead of stdout")
    comp = subs.add_parser("compile", help="compile Markdown or LaTeX")
    comp.add_argument("--target", choices=("markdown", "latex"), required=True)
    comp.add_argument("--output", required=True)
    refine = subs.add_parser("refine-language", help="apply guarded deterministic language cleanup to a copy")
    refine.add_argument("--section", required=True, help="section ID to refine")
    refine.add_argument("--output", required=True, help="new JSON file; the source IR is left untouched")
    inv = subs.add_parser("invalidate", help="list downstream objects affected by changed object IDs")
    inv.add_argument("ids", nargs="+", help="changed object ids")
    args = parser.parse_args(argv)
    try:
        if args.command == "workflow":
            if args.workflow_command == "classify":
                print(json.dumps(classify_task(args.prompt), indent=2))
            elif args.workflow_command == "initialize":
                print(json.dumps(initialize_paper_context(args.root, args.prompt), indent=2, ensure_ascii=False))
            elif args.workflow_command == "plan":
                result = make_paper_plan(args.prompt, args.root, args.paper_ir)
                _write_or_print(result, args.output)
            elif args.workflow_command == "prewrite":
                print(json.dumps(prewrite_check(args.prompt, args.root), indent=2, ensure_ascii=False))
            elif args.workflow_command == "postwrite":
                report = postwrite_audit(args.root, args.path, ir_path=args.paper_ir, **_gate_options(args))
                print(json.dumps(report, indent=2, ensure_ascii=False))
            elif args.workflow_command == "handoff":
                plan_path = Path(args.plan)
                plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
                report = postwrite_audit(args.root, args.path, ir_path=args.paper_ir, **_gate_options(args))
                if not isinstance(plan_data, dict):
                    raise ValueError("PaperPlan JSON must be an object")
                result = build_handoff(plan_data, report, args.human_review_completed)
                _write_or_print(result, args.output)
            return 0
        if args.command == "initialize":
            output_path, session = write_workflow_session(args.root, args.initialize_ir, args.output)
            print(json.dumps({"session": str(output_path), "initialized": session["initialized"], "paper_ir_version": session["paper_ir_version"], "capabilities": len(session["available_capabilities"]), "warnings": session["warnings"]}, indent=2, ensure_ascii=False))
            return 0
        if args.command in {"compile", "refine-language"} and not workflow_initialized(".", args.ir):
            print("paper: workflow is not initialized; run `paper initialize` before substantive manuscript execution (continuing without blocking)", file=sys.stderr)
        ir = load_ir(args.ir)
        if args.command == "validate":
            print("Paper IR valid (v0.1)")
        elif args.command == "audit":
            issues = audit(ir)
            print("Audit passed" if not issues else "\n".join(f"ERROR: {issue}" for issue in issues))
            return 0 if not issues else 1
        elif args.command == "status":
            print(json.dumps({"title": ir.get("metadata", {}).get("title"), "claims": len(ir.get("claims", [])), "evidence": len(ir.get("evidence", [])), "sections": len(ir.get("sections", [])), "audit_issues": audit(ir)}, indent=2))
        elif args.command == "warmup":
            print(json.dumps(to_warmup(ir), indent=2, ensure_ascii=False))
        elif args.command == "compile":
            compile_to(ir, args.target, args.output)
            print(f"Wrote {args.target} manuscript to {args.output}")
        elif args.command == "refine-language":
            section = next((s for s in ir.get("sections", []) if s.get("id") == args.section), None)
            if section is None:
                print(f"paper: unknown section id {args.section}", file=sys.stderr)
                return 2
            before = section.get("text", "")
            section["text"] = refine_text(before)
            Path(args.output).write_text(json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote refined copy to {args.output}; review the diff before accepting it")
        elif args.command == "invalidate":
            print(json.dumps(invalidation_report(ir, args.ids), indent=2))
        return 0
    except (ValidationError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"paper: {exc}", file=sys.stderr)
        return 2


def _add_gate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prose-modified", action="store_true", help="require a meaning-lock check")
    parser.add_argument("--language-original", help="file containing pre-edit prose")
    parser.add_argument("--language-revised", help="file containing revised prose")
    parser.add_argument("--locked-sentence", action="append", default=[], help="sentence that must remain byte-for-byte unchanged")
    parser.add_argument("--manuscript-output-modified", action="store_true", help="require an in-memory compile smoke test")
    parser.add_argument("--compile-target", choices=("markdown", "latex"))
    parser.add_argument("--upstream-evidence-changed", nargs="*", default=[], help="changed upstream evidence object IDs")
    parser.add_argument("--invalidation-reviewed", action="store_true", help="confirm the emitted dependency impact was reviewed")


def _gate_options(args: argparse.Namespace) -> dict[str, object]:
    def read_optional(path: str | None) -> str | None:
        return Path(path).read_text(encoding="utf-8") if path else None

    return {
        "prose_modified": args.prose_modified,
        "language_original": read_optional(args.language_original),
        "language_revised": read_optional(args.language_revised),
        "locked_sentences": args.locked_sentence,
        "manuscript_output_modified": args.manuscript_output_modified,
        "compile_target": args.compile_target,
        "upstream_evidence_changed": args.upstream_evidence_changed,
        "invalidation_reviewed": args.invalidation_reviewed,
    }


def _write_or_print(result: dict, output: str | None) -> None:
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
        print(f"Wrote workflow JSON to {target}")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    raise SystemExit(main())
