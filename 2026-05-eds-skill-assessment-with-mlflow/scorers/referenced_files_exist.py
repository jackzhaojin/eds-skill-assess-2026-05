"""Any relative paths referenced in SKILL.md (e.g. `references/foo.md`, `scripts/bar.js`) should resolve."""
from __future__ import annotations
import re
from pathlib import Path

REL_PATH_RE = re.compile(
    r"(?:\[[^\]]*\]\(|`)"
    r"([a-zA-Z0-9_\-./]+\.(?:md|json|js|ts|py|sh|html|css|yaml|yml))"
    r"(?:\)|`)"
)


def score(skill_md: Path) -> dict:
    text = skill_md.read_text()
    skill_dir = skill_md.parent
    candidates = set()
    for m in REL_PATH_RE.finditer(text):
        p = m.group(1)
        if p.startswith(("http", "/", "{{")) or "/" not in p and not p.endswith(".md"):
            continue
        if any(p == sentinel for sentinel in ("package.json", "CHANGELOG.md", "SKILL.md")):
            continue
        candidates.add(p)

    missing = []
    found = []
    for rel in sorted(candidates):
        target = (skill_dir / rel).resolve()
        if target.exists():
            found.append(rel)
        else:
            missing.append(rel)
    return {
        "scorer": "referenced_files_exist",
        "passed": not missing,
        "candidates": sorted(candidates),
        "found": found,
        "missing": missing,
    }
