## Project structure

```text
typecollect/
  README.md
  pyproject.toml
  typecollect.py
  tests/
    test_typecollect.py
```

Single-file package: `typecollect.py` is the only runtime module and is installed directly via `pyproject.toml` `[tool.setuptools] py-modules = ["typecollect"]`. No `src/` layout.
