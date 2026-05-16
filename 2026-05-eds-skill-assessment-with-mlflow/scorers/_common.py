"""Shared helpers for SKILL.md scorers."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Tuple, Dict, Any

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def split_frontmatter(skill_md: Path) -> Tuple[Dict[str, Any], str]:
    text = skill_md.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    try:
        import yaml
        fm = yaml.safe_load(raw) or {}
    except Exception:
        fm = {}
        for line in raw.splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body
