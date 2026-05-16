"""Frontmatter validity: name, description, license, version must be present and well-formed."""
from __future__ import annotations
from pathlib import Path
from ._common import split_frontmatter

REQUIRED = ["name", "description", "license"]
NAME_RE = r"^[a-z][a-z0-9-]{0,63}$"


def score(skill_md: Path) -> dict:
    import re
    fm, _ = split_frontmatter(skill_md)
    issues = []
    for k in REQUIRED:
        if k not in fm or not str(fm.get(k, "")).strip():
            issues.append(f"missing '{k}'")
    name = str(fm.get("name", ""))
    if name and not re.match(NAME_RE, name):
        issues.append(f"name '{name}' does not match {NAME_RE}")
    version = (fm.get("metadata") or {}).get("version") if isinstance(fm.get("metadata"), dict) else None
    if not version:
        issues.append("missing metadata.version")
    elif not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        issues.append(f"version '{version}' is not semver")
    if fm.get("license") and fm["license"] != "Apache-2.0":
        issues.append(f"license '{fm['license']}' is not the EDS-family default Apache-2.0")
    return {
        "scorer": "frontmatter_validity",
        "passed": not issues,
        "issues": issues,
        "frontmatter": {k: fm.get(k) for k in ("name", "description", "license", "metadata", "allowed-tools")},
    }
