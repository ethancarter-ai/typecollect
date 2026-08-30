# typecollect

Collect and report Python type annotations across a codebase.

## About

`typecollect` scans Python files and summarizes where type annotations are used: function signatures, variable assignments, class attributes, return types, and more. It helps teams measure type-coverage drift and find untyped hotspots without running mypy.

## Features

- Count annotated vs unannotated function definitions and signatures.
- Summarize annotated variable/class-attribute assignments.
- Report top files and top names by annotation density.
- Output in plain text or JSON.
- Optional import-only scan mode to skip function bodies.

## Installation

```bash
python -m pip install -e .
```

## Usage

```bash
typecollect .
typecollect src/ --format json
typecollect . --top 10
typecollect . --skip-imports
typecollect . --no-color
```

## Project structure

```
typecollect/
  README.md
  pyproject.toml
  typecollect.py
  tests/
    test_typecollect.py
```

## Tags / keywords

python, type-annotations, static-analysis, cli, tooling
