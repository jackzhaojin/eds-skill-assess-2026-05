#!/usr/bin/env python3
"""Claude Code Stop hook: tag the MLflow trace with skills the agent used.

Skill invocations reach the transcript via two distinct paths, both of which
this hook detects:

  1. Model-initiated: a `tool_use` block with name == "Skill". The skill slug
     lives in `input.skill`. MLflow's autolog already emits a `tool_Skill`
     span for these, but the skill name is not visible at trace-info level.

  2. User-initiated slash command: a user message containing
     `<command-name>NAME</command-name>`. This path bypasses the tool dispatch
     entirely, so MLflow emits no span for it. Built-in CLI commands
     (/compact, /clear, /help, /init, …) are excluded.

Both paths are aggregated into trace tags so an MLflow trace search like
`tags.skills_used LIKE '%create-site%'` can answer "which traces invoked
the create-site skill?".
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from pathlib import Path

# Slash commands shipped by Claude Code itself, not skills. Drop these so the
# `skills_used` tag stays focused on actual skill invocations.
BUILTIN_COMMANDS = {
    "compact", "clear", "help", "init", "config", "memory", "model",
    "vim", "status", "release-notes", "permissions", "login", "logout",
    "cost", "doctor", "bug", "exit", "quit", "review", "ide",
    "agents", "mcp", "hooks", "terminal-setup", "add-dir", "resume",
    "pr_comments", "fast",
}

COMMAND_TAG_RE = re.compile(r"<command-name>([^<]+)</command-name>")

LOG_DIR = Path.home() / ".claude" / "mlflow"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "skill_tracker.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("skill_tracker")


def read_hook_input() -> dict:
    return json.loads(sys.stdin.read())


def emit_response(stop_reason: str | None = None) -> None:
    out = {"continue": True}
    if stop_reason:
        out["stopReason"] = stop_reason
    print(json.dumps(out))


def extract_invocations(transcript_path: str) -> list[dict]:
    invocations: list[dict] = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = entry.get("message") if isinstance(entry, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            ts = entry.get("timestamp")

            if isinstance(content, list):
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "tool_use"
                        and part.get("name") == "Skill"
                    ):
                        skill = (part.get("input") or {}).get("skill")
                        if skill:
                            invocations.append({
                                "skill": skill.strip(),
                                "source": "model_tool_call",
                                "timestamp": ts,
                            })

            if isinstance(content, str):
                for m in COMMAND_TAG_RE.finditer(content):
                    name = m.group(1).strip().lstrip("/").strip()
                    if not name or name in BUILTIN_COMMANDS:
                        continue
                    invocations.append({
                        "skill": name,
                        "source": "slash_command",
                        "timestamp": ts,
                    })

    return invocations


def find_trace(session_id: str, retries: int = 6, delay: float = 0.7):
    """Find the trace MLflow autolog just wrote for this Claude session.

    Retries because both Stop hooks fire in parallel; the MLflow hook may not
    have flushed the trace by the time we run.
    """
    import mlflow
    from mlflow.tracking import MlflowClient

    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "Default")
    client = MlflowClient()
    exp = client.get_experiment_by_name(experiment_name)
    if exp is None:
        log.warning("experiment %r not found", experiment_name)
        return None, None

    for attempt in range(retries):
        try:
            traces = mlflow.search_traces(
                locations=[exp.experiment_id],
                max_results=25,
                order_by=["timestamp DESC"],
                return_type="list",
            )
        except Exception as e:
            log.warning("search_traces attempt %d failed: %s", attempt, e)
            traces = []

        for t in traces:
            md = getattr(t.info, "trace_metadata", {}) or {}
            if md.get("mlflow.trace.session") == session_id:
                return client, t

        time.sleep(delay)

    log.warning("no trace found for session_id=%s after %d retries", session_id, retries)
    return client, None


def apply_tags(client, trace, invocations: list[dict]) -> None:
    skills = sorted({inv["skill"] for inv in invocations})
    sources = sorted({inv["source"] for inv in invocations})
    counts: dict[str, int] = {}
    for inv in invocations:
        counts[inv["skill"]] = counts.get(inv["skill"], 0) + 1

    tags = {
        "skills_used": json.dumps(skills),
        "skills_used_count": str(len(invocations)),
        "skills_unique_count": str(len(skills)),
        "skill_invocation_sources": json.dumps(sources),
        "skills_used_breakdown": json.dumps(counts),
    }
    for k, v in tags.items():
        client.set_trace_tag(trace.info.trace_id, k, v)
    log.info("tagged trace %s with skills=%s", trace.info.trace_id, skills)


def main() -> None:
    try:
        hook_input = read_hook_input()
    except Exception as e:
        log.error("bad hook input: %s", e)
        emit_response()
        return

    session_id = hook_input.get("session_id")
    transcript_path = hook_input.get("transcript_path")

    if not session_id or not transcript_path or not Path(transcript_path).exists():
        log.info("missing session_id or transcript_path; skipping")
        emit_response()
        return

    try:
        invocations = extract_invocations(transcript_path)
    except Exception as e:
        log.error("transcript scan failed: %s", e, exc_info=True)
        emit_response()
        return

    if not invocations:
        log.info("session=%s: no skill invocations found", session_id)
        emit_response()
        return

    try:
        client, trace = find_trace(session_id)
        if trace is None:
            emit_response(stop_reason="skill-tracker: trace not found yet")
            return
        apply_tags(client, trace, invocations)
        emit_response()
    except Exception as e:
        log.error("tag write failed: %s", e, exc_info=True)
        emit_response(stop_reason=f"skill-tracker error: {e}")


if __name__ == "__main__":
    main()
