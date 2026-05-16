"""Must-not-have signals from rubric.md."""
from __future__ import annotations
import re
from pathlib import Path

PATTERNS = [
    ("hardcoded secret/token",
     r"\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|Bearer\s+ey[A-Za-z0-9._-]{20,}|AKIA[0-9A-Z]{16})\b",
     "block"),
    ("stale copyright year (© 2024) in templated content",
     r"©\s*2024", "warn"),
    ("disables verification / skips preview / bypasses IMS",
     r"(--no-verify|skip\s+preview|bypass(?:es)?\s+(?:the\s+)?IMS|disable\s+verification)",
     "block"),
    ("clobbers existing repo/content without confirm",
     r"(--force(?!.*confirm)|overwrite without confirm)",
     "warn"),
    ("downstream concern conflation (CDN, RUM, custom domain configuration)",
     r"(akamai|RUM\b|OpTel|push invalidation|domain keys)",
     "warn"),
]


def score(skill_md: Path) -> dict:
    text = skill_md.read_text()
    hits = []
    rows = []
    for label, pat, sev in PATTERNS:
        m = re.findall(pat, text, flags=re.IGNORECASE)
        present = bool(m)
        rows.append({"label": label, "pattern": pat, "found": present, "severity": sev, "matches": m[:3]})
        if present:
            hits.append({"label": label, "severity": sev, "matches": m[:3]})
    block_hits = [h for h in hits if h["severity"] == "block"]
    return {
        "scorer": "must_not_have_patterns",
        "passed": not block_hits,
        "hits": hits,
        "blocking_hits": block_hits,
        "details": rows,
    }
