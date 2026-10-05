"""Command line interface for validating, auditing, compiling, and warming up a paper."""

import argparse
import json
import sys
from pathlib import Path

from .audit import audit, invalidation_report
from .compiler import compile_to
from .ir import ValidationError, load_ir, to_warmup
from .language import refine_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paper", description="Paper IR centered research-to-manuscript tools")
    parser.add_argument("--ir", default="paper.json", help="Paper IR JSON path (default: paper.json)")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate", help="validate IR structure and references")
    subs.add_parser("audit", help="run deterministic scientific consistency checks")
    subs.add_parser("status", help="summarize claims, evidence, and sections")
    subs.add_parser("warmup", help="emit a compact project handoff JSON")
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
