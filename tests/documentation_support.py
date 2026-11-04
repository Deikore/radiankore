"""Load executable examples from published Markdown."""

import re
from pathlib import Path
from typing import Any

import pytest


def python_blocks(path: Path) -> list[str]:
    """Read the Python code actually published, without duplicating its examples."""
    return re.findall(r"```python\n(.*?)```", path.read_text(), re.DOTALL)


def namespace(path: Path) -> dict[str, Any]:
    """Load real Markdown examples without running command-line entry points."""
    if not path.is_file():
        pytest.skip("Documentation is excluded from this distribution.")
    values: dict[str, Any] = {"__name__": "published_examples"}
    for number, block in enumerate(python_blocks(path)):
        exec(compile(block, f"{path}:block-{number}", "exec"), values)
    return values
