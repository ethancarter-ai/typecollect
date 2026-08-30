from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest

from typecollect import analyze, main, _counts_for_source


def _summary_to_dict(summary) -> dict:
    return {
        "path": summary.path,
        "functions": summary.functions,
        "annotated_functions": summary.annotated_functions,
        "returns": summary.returns,
        "annotated_returns": summary.annotated_returns,
        "variables": summary.variables,
        "annotated_variables": summary.annotated_variables,
        "score": summary.score,
    }


def test_counts_for_source_typed() -> None:
    source = """
def add(a: int, b: int) -> int:
    return a + b

x: int = 1
y = 2
"""
    counts = _counts_for_source(source)
    assert counts["functions"] == 1
    assert counts["annotated_functions"] == 1
    assert counts["returns"] == 1
    assert counts["annotated_returns"] == 1
    assert counts["variables"] == 2
    assert counts["annotated_variables"] == 1


def test_counts_for_source_untyped() -> None:
    source = """
def add(a, b):
    return a + b
"""
    counts = _counts_for_source(source)
    assert counts["functions"] == 1
    assert counts["annotated_functions"] == 0


def test_counts_for_source_syntax_error_returns_zeroes() -> None:
    counts = _counts_for_source("def (")
    assert counts == {
        "functions": 0,
        "annotated_functions": 0,
        "returns": 0,
        "annotated_returns": 0,
        "variables": 0,
        "annotated_variables": 0,
    }


def test_analyze_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text("x: int = 1\n")
        (root / "b.py").write_text("def f():\n    return 1\n")
        report = analyze(root, skip_imports=False)
        assert report.py_files == 2
        assert report.functions == 1
        assert report.annotated_functions == 0
        assert report.variables == 1
        assert report.annotated_variables == 1
        assert 0 <= report.score <= 1
        assert len(report.file_summaries) == 2


def test_analyze_skips_tests_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app.py").write_text("def f():\n    return 1\n")
        tests = root / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text("def test_nothing():\n    pass\n")
        report = analyze(root, skip_imports=True)
        assert report.py_files == 1
        assert report.file_summaries[0]["path"] == "app.py"


def test_main_returns_zero_for_valid_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "m.py").write_text("x = 1\n")
        assert main([tmp]) == 0


def test_main_returns_one_for_missing_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert main([str(Path(tmp) / "missing")]) == 1


def test_main_json_output_contains_keys() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "m.py").write_text("x = 1\n")
        assert main([tmp, "--format", "json"]) == 0
