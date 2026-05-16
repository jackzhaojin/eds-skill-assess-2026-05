# Skill Evaluation Rubric

**Skill under test:** `./skill-under-test/` (Adobe `create-site` v1.1.0)
**Source:** https://github.com/adobe/skills/tree/main/plugins/aem/edge-delivery-services/skills/create-site
**Evaluator:** Jack — Senior Manager / Technical Architect, deep EDS background
**Date:** 2026-05

---

## Vendor & Domain Context

- **Vendor:** Adobe (first-party, distributed under Apache-2.0)
- **Domain:** AEM Edge Delivery Services — site creation / onboarding flow
- **Target invoker:** A coding agent (Claude Code, Codex, etc.) acting on behalf of a developer who wants to spin up a new EDS site from the `adobe/aem-boilerplate` template
- **Co-skills in the same plugin:** 20 EDS skills in this repo (`page-import`, `content-driven-development`, `building-blocks`, etc.) — adjacency matters for trigger precision
- **Out-of-scope for this skill (by design):** post-launch concerns (Akamai BYO CDN config, RUM/OpTel, domain keys, push invalidation, broken-link audits, `.html` URL variant handling). These belong to separate skills or runbooks.

---

## Scoring Weights (sum to 1.0)

| Dimension | Weight | Mode |
|---|---:|---|
| Trigger precision | 0.20 | LLM judge |
| Instruction clarity & completeness | 0.20 | LLM judge |
| Domain correctness (EDS-specific) | 0.25 | LLM judge + rule-based |
| Error & recovery coverage | 0.10 | LLM judge |
| Human-in-loop signaling | 0.05 | LLM judge |
| Safety & idempotency | 0.10 | LLM judge |
| Currency & link health | 0.05 | Rule-based |
| Frontmatter & structural validity | 0.05 | Rule-based |

Improvability suggestions are reported separately (qualitative, not scored).

---

## Must-have (failing any one drops domain-correctness score by ≥1 point on 5-pt scale)

- `aem-code-sync` installation flagged as a human action with the canonical install URL
- Explicit verify checks after each major step (HTTP status codes, JSON shape)
- Distinguishes itself from `page-import` (existing pages) and `content-driven-development` (existing site) in the description or a "Do NOT use" section
- DA token lifecycle handled: cache check → refresh path → manual fallback
- Bearer token on preview requests called out (DA-sourced content quirk)
- Reference links to canonical docs: `aem.live`, `da.live/docs`, boilerplate repo, admin API

## Must-not-have (any occurrence is an automatic flag)

- Hardcoded credentials, tokens, or secrets in templates or examples
- Stale dates baked into templates (e.g. `© 2024` in footer.html when the skill ships into 2026+)
- Steps that would clobber existing repos or DA content without confirmation
- Conflation with downstream concerns the skill doesn't own (CDN, RUM, custom domain) — this skill should hand off, not stretch
- Recommendations to disable verification, skip preview, or bypass the IMS auth flow

---

## Comparison References

- **Anthropic best practices for SKILL.md:** clear `description` field that disambiguates when to load, progressive disclosure, examples, allowed-tools declaration if applicable
- **Sibling EDS skills:** read 2–3 sibling skills in `../adobe-skills-repo/plugins/aem/edge-delivery-services/skills/` (e.g. `page-import`, `content-driven-development`, `building-blocks`) to assess consistency of voice, structure, and cross-reference

---

## Pre-run Notes from the Human Judge

A few things I want the judges to weigh in on specifically — not as fixed criteria, just signal:

1. **Trigger precision around onboarding ambiguity.** "Set up a new site" can mean a brand-new repo (this skill) or an import from an existing site (`page-import`). The description handles this with "no GitHub repository or DA content exists yet" — does that hold up under realistic, fuzzy user phrasings? Spot the failure modes.

2. **The `--public` default in Step 2.** Many enterprise EDS rollouts need private repos. The skill doesn't expose a visibility toggle. Is that a defensible default or a gap?

3. **Hardcoded `© 2024` in `footer.html` template (line 211).** A bug, a stylistic choice, or fine because the user will edit it anyway? I lean "bug" but want the judge's view.

4. **Step 3 wait-for-human pattern.** Is "Reply 'done' when complete" the right shape, or should it instruct the agent to poll `admin.hlx.page/status` automatically until success? Trade-off between agent autonomy and user clarity.

5. **No allowed-tools frontmatter field.** Anthropic's skill-creator pattern suggests declaring `allowed-tools` (Bash, Read, Write, WebFetch). Does omission of this matter for create-site, which clearly needs Bash + WebFetch?

6. **Reference link health.** Surface any 404s among the eight reference URLs at the bottom of the SKILL.md — this is a rule-based check, but the LLM judge should weight broken canonical refs heavier than broken nice-to-haves.

---

## Output

Produce:
1. A scorecard with each dimension scored 1–5 plus a one-paragraph rationale per dimension
2. A weighted total (0–5)
3. A ranked list of improvement suggestions (each with: line reference, suggested change, expected score impact)
4. A trace in MLflow with all judge rationales attached

Save the scorecard to `./scorecards/2026-05-create-site.md`.
