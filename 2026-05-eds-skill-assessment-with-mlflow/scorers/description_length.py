"""Anthropic guidance: SKILL.md description should be <=1024 chars (single field, used for trigger routing)."""
from __future__ import annotations
from pathlib import Path
from ._common import split_frontmatter

LIMIT = 1024


def score(skill_md: Path) -> dict:
    fm, _ = split_frontmatter(skill_md)
    desc = str(fm.get("description", ""))
    n = len(desc)
    return {
        "scorer": "description_length",
        "passed": 1 <= n <= LIMIT,
        "length": n,
        "limit": LIMIT,
        "description": desc,
    }
