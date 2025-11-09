from __future__ import annotations

from pathlib import Path

THIS_DIR = Path(__file__).parent
DOCS_DIR = THIS_DIR.parent
PROJECT_ROOT = DOCS_DIR.parent


def on_pre_build(**_) -> None:
    """Add changelog to docs/changelog.md"""
    cl_now = PROJECT_ROOT.joinpath("CHANGELOG.md").read_text(encoding="utf-8")

    f_doc = DOCS_DIR.joinpath("changelog.md")
    if not f_doc.is_file() or f_doc.read_text(encoding="utf-8") != cl_now:
        f_doc.write_text(cl_now, encoding="utf-8")
