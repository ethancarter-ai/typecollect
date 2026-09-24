from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, TextIO


@dataclass
class FileSummary:
    path: str
    functions: int = 0
    annotated_functions: int = 0
    returns: int = 0
    annotated_returns: int = 0
    variables: int = 0
    annotated_variables: int = 0

    @property
    def score(self) -> float:
        denom = (self.functions + self.returns + self.variables) or 1
        return round((self.annotated_functions + self.annotated_returns + self.annotated_variables) / denom, 4)


@dataclass
class Report:
    root: str
    files: int = 0
    py_files: int = 0
    functions: int = 0
    annotated_functions: int = 0
    returns: int = 0
    annotated_returns: int = 0
    variables: int = 0
    annotated_variables: int = 0
    file_summaries: list[dict] = field(default_factory=list)

    @property
    def score(self) -> float:
        denom = (self.functions + self.returns + self.variables) or 1
        return round((self.annotated_functions + self.annotated_returns + self.annotated_variables) / denom, 4)


def _function_is_annotated(node: ast.FunctionDef) -> bool:
    if node.returns is not None:
        return True
    return any(getattr(arg, "annotation", None) is not None for arg in node.args.args)

def _walk(node: ast.AST, kind: str, counts: dict[str, int]) -> None:
    if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
        counts["functions"] += 1
        if _function_is_annotated(node):
            counts["annotated_functions"] += 1
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                counts["returns"] += 1
                if node.returns is not None:
                    counts["annotated_returns"] += 1
    if isinstance(node, ast.AnnAssign):
        counts["variables"] += 1
        counts["annotated_variables"] += 1
    elif isinstance(node, ast.Assign):
        counts["variables"] += 1
    for child in ast.iter_child_nodes(node):
        _walk(child, kind, counts)


def _counts_for_source(source: str) -> dict[str, int]:
    counts: dict[str, int] = {
        "functions": 0,
        "annotated_functions": 0,
        "returns": 0,
        "annotated_returns": 0,
        "variables": 0,
        "annotated_variables": 0,
    }
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return counts
    _walk(tree, "", counts)
    return counts


def _python_files(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield Path(dirpath) / filename


def analyze(root: Path, skip_imports: bool) -> Report:
    root = root.resolve()
    report = Report(root=str(root))
    summaries: list[FileSummary] = []

    for path in sorted(_python_files(root)):
        rel = os.path.relpath(path, root)
        if skip_imports:
            if any(part == "tests" for part in path.relative_to(root).parts):
                continue
        source = path.read_text(encoding="utf-8")
        counts = _counts_for_source(source)
        summary = FileSummary(
            path=rel,
            functions=counts["functions"],
            annotated_functions=counts["annotated_functions"],
            returns=counts["returns"],
            annotated_returns=counts["annotated_returns"],
            variables=counts["variables"],
            annotated_variables=counts["annotated_variables"],
        )
        summaries.append(summary)
        report.py_files += 1
        report.functions += summary.functions
        report.annotated_functions += summary.annotated_functions
        report.returns += summary.returns
        report.annotated_returns += summary.annotated_returns
        report.variables += summary.variables
        report.annotated_variables += summary.annotated_variables

    summaries.sort(key=lambda item: item.score, reverse=True)
    report.file_summaries = [
        {
            "path": item.path,
            "functions": item.functions,
            "annotated_functions": item.annotated_functions,
            "returns": item.returns,
            "annotated_returns": item.annotated_returns,
            "variables": item.variables,
            "annotated_variables": item.annotated_variables,
            "score": item.score,
        }
        for item in summaries
    ]
    return report


def _format_text(report: Report, top: int, color: bool) -> str:
    lines = [
        f"typecollect {report.root}",
        f"python files : {report.py_files}",
        f"functions    : {report.functions} ({report.annotated_functions} annotated)",
        f"returns      : {report.returns} ({report.annotated_returns} annotated)",
        f"variables    : {report.variables} ({report.annotated_variables} annotated)",
        f"score        : {report.score:.2%}",
        "",
        "Top files by annotation density:",
    ]
    for summary in report.file_summaries[: max(top, 0)]:
        total = summary["functions"] + summary["returns"] + summary["variables"]
        annotated = (
            summary["annotated_functions"]
            + summary["annotated_returns"]
            + summary["annotated_variables"]
        )
        lines.append(
            f"  {summary['path']}: {summary['score']:.2%} ({annotated}/{total})"
        )
    return "\n".join(lines) + "\n"


def _format_json(report: Report) -> str:
    payload = {
        "root": report.root,
        "python_files": report.py_files,
        "functions": report.functions,
        "annotated_functions": report.annotated_functions,
        "returns": report.returns,
        "annotated_returns": report.annotated_returns,
        "variables": report.variables,
        "annotated_variables": report.annotated_variables,
        "score": report.score,
        "files": report.file_summaries,
    }
    return json.dumps(payload, indent=2) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Python type annotation coverage.")
    parser.add_argument("path", nargs="?", default=".", help="Project root to scan")
    parser.add_argument("--format", choices=["plain", "json"], default="plain", help="Output format")
    parser.add_argument("--top", type=int, default=5, help="Number of top files to show")
    parser.add_argument("--skip-imports", action="store_true", help="Skip test directories")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, stdin: TextIO | None = None) -> int:
    del stdin
    args = parse_args(argv)
    root = Path(args.path)
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1
    report = analyze(root, args.skip_imports)
    if args.format == "json":
        sys.stdout.write(_format_json(report))
    else:
        sys.stdout.write(_format_text(report, args.top, not args.no_color))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
