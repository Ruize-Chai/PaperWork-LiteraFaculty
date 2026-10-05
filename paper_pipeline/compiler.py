"""Simple deterministic manuscript backends; IR remains the source of truth."""

from pathlib import Path
from typing import Any


def _tex(value: str) -> str:
    return (value.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
            .replace("$", r"\$").replace("#", r"\#").replace("_", r"\_").replace("{", r"\{").replace("}", r"\}"))


def compile_markdown(ir: dict[str, Any]) -> str:
    meta = ir.get("metadata", {})
    lines = [f"# {meta.get('title') or 'Untitled manuscript'}", ""]
    if meta.get("authors"):
        lines.extend([", ".join(a if isinstance(a, str) else a.get("name", "") for a in meta["authors"]), ""])
    for section in ir.get("sections", []):
        lines.extend([f"## {section.get('title') or section.get('id')}", "", section.get("text", ""), ""])
    return "\n".join(lines).rstrip() + "\n"


def compile_latex(ir: dict[str, Any]) -> str:
    meta = ir.get("metadata", {})
    lines = [r"\documentclass{article}", r"\usepackage[utf8]{inputenc}", r"\begin{document}",
             r"\title{" + _tex(meta.get("title") or "Untitled manuscript") + "}"]
    authors = [a if isinstance(a, str) else a.get("name", "") for a in meta.get("authors", [])]
    if authors:
        lines.append(r"\author{" + _tex(" \and ".join(authors)) + "}")
    lines += [r"\maketitle"]
    for section in ir.get("sections", []):
        lines += [r"\section{" + _tex(section.get("title") or section.get("id", "")) + "}", section.get("text", ""), ""]
    lines.append(r"\end{document}")
    return "\n".join(lines) + "\n"


def compile_to(ir: dict[str, Any], target: str, output: str | Path) -> None:
    content = compile_markdown(ir) if target == "markdown" else compile_latex(ir)
    Path(output).write_text(content, encoding="utf-8")

