"""Must-have signals from rubric.md. Each pattern is a (label, regex, severity) tuple."""
from __future__ import annotations
import re
from pathlib import Path

PATTERNS = [
    ("aem-code-sync as human action with canonical install URL",
     r"aem-code-sync.*?(human action|user must complete it).*?github\.com/apps/aem-code-sync/installations/new",
     "block"),
    ("explicit verify checks (HTTP status codes)",
     r"(verify|success).{0,40}(http\s*\d{3}|status code|\b20[01]\b|\b40\d\b)",
     "block"),
    ("distinguishes from page-import",
     r"page-import",
     "block"),
    ("distinguishes from content-driven-development",
     r"content-driven-development",
     "block"),
    ("DA token cache check path",
     r"(~/\.aem/da-token\.json|cached token|token cache)",
     "block"),
    ("DA token refresh/manual fallback path",
     r"(da-auth-helper\s+token|refresh|Manual token)",
     "block"),
    ("Bearer token called out on preview requests",
     r"(preview.{0,80}Bearer|DA-sourced content (requires|needs) (the )?Bearer)",
     "block"),
    ("Reference to aem.live",
     r"https?://(?:www\.)?aem\.live", "block"),
    ("Reference to da.live/docs",
     r"https?://da\.live/docs", "block"),
    ("Reference to aem-boilerplate",
     r"github\.com/adobe/aem-boilerplate", "block"),
    ("Reference to admin API",
     r"(admin\.hlx\.page|aem\.live/docs/admin)", "block"),
]


def score(skill_md: Path) -> dict:
    text = skill_md.read_text()
    rows = []
    missed = []
    for label, pat, sev in PATTERNS:
        ok = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL) is not None
        rows.append({"label": label, "pattern": pat, "found": ok, "severity": sev})
        if not ok:
            missed.append(label)
    return {
        "scorer": "must_have_patterns",
        "passed": not missed,
        "missing": missed,
        "details": rows,
    }
