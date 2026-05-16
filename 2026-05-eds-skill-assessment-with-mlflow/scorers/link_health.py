"""HEAD-check every absolute URL in SKILL.md, with extra weight on the Reference block."""
from __future__ import annotations
import re
from pathlib import Path

import requests

URL_RE = re.compile(r"https?://[^\s)\"`'<>]+")
REFERENCE_HDR = re.compile(r"^##\s+Reference", re.MULTILINE)


def _find_reference_block(text: str) -> str:
    m = REFERENCE_HDR.search(text)
    if not m:
        return ""
    return text[m.start():]


def _norm(u: str) -> str:
    return u.rstrip(".,;:)]")


def _check(url: str) -> dict:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10,
                          headers={"User-Agent": "skill-assess-2026-05/1.0"})
        status = r.status_code
        if status == 405 or status >= 400:
            r = requests.get(url, allow_redirects=True, timeout=15,
                             headers={"User-Agent": "skill-assess-2026-05/1.0"},
                             stream=True)
            status = r.status_code
            r.close()
        return {"url": url, "status": status, "ok": status < 400, "final_url": r.url}
    except Exception as e:
        return {"url": url, "status": None, "ok": False, "error": str(e)[:200]}


def score(skill_md: Path) -> dict:
    text = skill_md.read_text()
    ref_block = _find_reference_block(text)

    all_urls = sorted({_norm(u) for u in URL_RE.findall(text)})
    ref_urls = sorted({_norm(u) for u in URL_RE.findall(ref_block)})

    skip_template = lambda u: "{{" in u or "}}" in u
    all_urls = [u for u in all_urls if not skip_template(u)]
    ref_urls = [u for u in ref_urls if not skip_template(u)]

    results = [_check(u) for u in all_urls]
    by_url = {r["url"]: r for r in results}
    ref_results = [by_url[u] for u in ref_urls if u in by_url]

    broken_all = [r for r in results if not r["ok"]]
    broken_ref = [r for r in ref_results if not r["ok"]]

    return {
        "scorer": "link_health",
        "passed": not broken_ref,
        "total_urls_checked": len(results),
        "reference_urls_checked": len(ref_results),
        "broken_total": len(broken_all),
        "broken_reference": len(broken_ref),
        "broken_reference_details": broken_ref,
        "broken_other_details": [r for r in broken_all if r not in broken_ref],
        "results": results,
    }
