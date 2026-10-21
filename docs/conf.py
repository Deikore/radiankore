"""Sphinx configuration, independent of runtime signing dependencies."""

import os
import tomllib
from pathlib import Path

_metadata = tomllib.loads(
    (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
)["project"]

project = _metadata["name"]
author = "Deikore SAS"
copyright = "2026, Deikore SAS"
release = _metadata["version"]
version = release
language = "es"

extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}
root_doc = "index"
myst_heading_anchors = 3
exclude_patterns = ["_build", "references/**"]

html_theme = "furo"
html_title = f"radiankore {release}"
html_baseurl = os.environ.get(
    "READTHEDOCS_CANONICAL_URL", "https://radiankore.readthedocs.io/"
)
html_theme_options = {
    "source_repository": "https://github.com/Deikore/radiankore/",
    "source_branch": "HEAD",
    "source_directory": "docs/",
}
