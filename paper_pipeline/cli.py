"""Command line interface for validating, auditing, compiling, and warming up a paper."""

import argparse
import json
import sys
from pathlib import Path

from .audit import audit, invalidation_report
from .compiler import compile_to
from .ir import ValidationError, load_ir, to_warmup
from .language import refine_text
from .workflow import classify_task, initialize_paper_context, make_paper_plan, prewrite_check, postwrite_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paper", description="Paper IR centered research-to-manuscript tools")
    parser.add_argument("--ir", default="paper.json", help="Paper IR JSON path (default: paper.json)")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate", help="validate IR structure and references")
    subs.add_parser("audit", help="run deterministic scientific consistency checks")
    subs.add_parser("status", help="summarize claims, evidence, and sections")
    subs.add_parser("warmup", help="emit a compact project handoff JSON")
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
    before = workflow_sub.add_parser("prewrite", help="check initialization before a manuscript write")
    before.add_argument("prompt")
    before.add_argument("--root", default=".")
    after = workflow_sub.add_parser("postwrite", help="run post-write manuscript checks")
    after.add_argument("--root", default=".")
    after.add_argument("--path", action="append", default=[], help="changed manuscript or figure path")
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
                print(json.dumps(make_paper_plan(args.prompt, args.root), indent=2, ensure_ascii=False))
            elif args.workflow_command == "prewrite":
                print(json.dumps(prewrite_check(args.prompt, args.root), indent=2, ensure_ascii=False))
            elif args.workflow_command == "postwrite":
                print(json.dumps(postwrite_audit(args.root, args.path), indent=2, ensure_ascii=False))
            return 0
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
    except (ValidationError, OSError) as exc:
        print(f"paper: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
