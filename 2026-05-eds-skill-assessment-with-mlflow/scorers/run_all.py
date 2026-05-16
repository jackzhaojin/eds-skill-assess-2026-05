"""Run all rule-based scorers and dump JSON for MLflow logging + scorecard."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scorers import (
    frontmatter_validity,
    description_length,
    referenced_files_exist,
    must_have_patterns,
    must_not_have_patterns,
    link_health,
)


def main(skill_md: Path, out_path: Path) -> dict:
    results = {
        "skill_md_path": str(skill_md),
        "scorers": {
            "frontmatter_validity": frontmatter_validity.score(skill_md),
            "description_length": description_length.score(skill_md),
            "referenced_files_exist": referenced_files_exist.score(skill_md),
            "must_have_patterns": must_have_patterns.score(skill_md),
            "must_not_have_patterns": must_not_have_patterns.score(skill_md),
            "link_health": link_health.score(skill_md),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str))
    return results


if __name__ == "__main__":
    skill = ROOT / "skill-under-test" / "SKILL.md"
    out = ROOT / "scorers" / "results.json"
    res = main(skill, out)
    summary = {name: r.get("passed") for name, r in res["scorers"].items()}
    print(json.dumps({"out": str(out), "passed": summary}, indent=2))
