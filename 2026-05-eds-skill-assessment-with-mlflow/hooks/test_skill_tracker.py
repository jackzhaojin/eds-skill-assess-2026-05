#!/usr/bin/env python3
"""Self-test for skill_tracker.py.

Builds a synthetic JSONL transcript that exercises both invocation paths
(model-initiated Skill tool call, user-initiated slash command, plus the
built-in /compact that must be filtered out), runs the parser, then runs the
full hook against a real MLflow trace and reads the tags back.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from skill_tracker import BUILTIN_COMMANDS, extract_invocations  # noqa: E402

REPO_ROOT = HERE.parent.parent
PY = REPO_ROOT / ".venv" / "bin" / "python"
HOOK = HERE / "skill_tracker.py"


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_synthetic_transcript(path: Path) -> None:
    """Write a JSONL with: slash command, model Skill tool call, built-in
    /compact (must be ignored), and a second slash command for the same skill
    (counts should aggregate).
    """
    entries = [
        # User invokes /create-site (slash command path)
        {
            "type": "user",
            "timestamp": ts(),
            "message": {
                "role": "user",
                "content": "<command-name>/create-site</command-name>\n<command-message>creating site</command-message>",
            },
        },
        # Assistant invokes Skill tool (model-initiated path)
        {
            "type": "assistant",
            "timestamp": ts(),
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Loading the skill..."},
                    {
                        "type": "tool_use",
                        "id": "toolu_test_1",
                        "name": "Skill",
                        "input": {"skill": "page-import", "args": "https://example.com"},
                    },
                ],
            },
        },
        # User runs /compact (built-in — MUST be filtered)
        {
            "type": "user",
            "timestamp": ts(),
            "message": {
                "role": "user",
                "content": "<command-name>/compact</command-name>",
            },
        },
        # User invokes /create-site again (count aggregation)
        {
            "type": "user",
            "timestamp": ts(),
            "message": {
                "role": "user",
                "content": "<command-name>create-site</command-name>",  # no leading slash
            },
        },
    ]
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def test_parser(transcript_path: Path) -> None:
    print("== parser test ==")
    invs = extract_invocations(str(transcript_path))
    skills_by_source: dict[str, list[str]] = {}
    for inv in invs:
        skills_by_source.setdefault(inv["source"], []).append(inv["skill"])

    print(f"  total invocations: {len(invs)}")
    for src, names in skills_by_source.items():
        print(f"  - {src}: {names}")

    seen_skills = {inv["skill"] for inv in invs}
    expected = {"create-site", "page-import"}
    assert seen_skills == expected, f"FAIL: expected {expected}, got {seen_skills}"
    assert "compact" not in seen_skills, "FAIL: built-in /compact leaked through"
    assert sum(1 for inv in invs if inv["skill"] == "create-site") == 2, (
        "FAIL: create-site should be seen twice"
    )
    assert any(inv["source"] == "model_tool_call" for inv in invs), "FAIL: no model_tool_call seen"
    assert any(inv["source"] == "slash_command" for inv in invs), "FAIL: no slash_command seen"
    print("  ✓ parser correctness checks passed")


def test_hook_against_real_trace() -> None:
    """Feed the synthetic transcript through the hook script, targeting a real
    MLflow trace so we can verify the tag write end-to-end."""
    print("\n== end-to-end hook test ==")

    # Use the live session that has a known trace, but point transcript_path
    # at our synthetic file so we exercise both invocation paths.
    real_session_id = "06547bf2-43e2-4706-aeb9-0d8fb9695eaa"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, prefix="synth_"
    ) as tf:
        synth_path = Path(tf.name)
    build_synthetic_transcript(synth_path)

    hook_input = {
        "session_id": real_session_id,
        "transcript_path": str(synth_path),
    }

    env = os.environ.copy()
    env.setdefault("MLFLOW_TRACKING_URI", "http://127.0.0.1:5050")
    env.setdefault("MLFLOW_EXPERIMENT_NAME", "eds-skill-assessment-2026-05")

    print(f"  feeding hook: session={real_session_id}, transcript={synth_path.name}")
    result = subprocess.run(
        [str(PY), str(HOOK)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    print(f"  hook stdout: {result.stdout.strip()}")
    if result.stderr.strip():
        print(f"  hook stderr: {result.stderr.strip()}")
    assert result.returncode == 0, f"hook exited {result.returncode}"

    # Read tags back
    from mlflow.tracking import MlflowClient

    client = MlflowClient(tracking_uri=env["MLFLOW_TRACKING_URI"])
    exp = client.get_experiment_by_name(env["MLFLOW_EXPERIMENT_NAME"])
    traces = client.search_traces(
        locations=[exp.experiment_id], max_results=50, order_by=["timestamp DESC"]
    )
    target = None
    for t in traces:
        if (t.info.trace_metadata or {}).get("mlflow.trace.session") == real_session_id:
            target = t
            break

    assert target is not None, f"no trace found for session {real_session_id}"
    tags = target.info.tags or {}
    print(f"  trace_id: {target.info.trace_id}")
    print("  trace tags relating to skills:")
    for k in sorted(tags):
        if "skill" in k.lower():
            print(f"    {k}: {tags[k]}")

    skills_used = json.loads(tags.get("skills_used", "[]"))
    assert set(skills_used) == {"create-site", "page-import"}, (
        f"FAIL: skills_used = {skills_used}"
    )
    assert int(tags.get("skills_used_count", 0)) == 3, "FAIL: total count"
    assert int(tags.get("skills_unique_count", 0)) == 2, "FAIL: unique count"
    sources = json.loads(tags.get("skill_invocation_sources", "[]"))
    assert set(sources) == {"model_tool_call", "slash_command"}, "FAIL: sources"

    breakdown = json.loads(tags.get("skills_used_breakdown", "{}"))
    assert breakdown.get("create-site") == 2, "FAIL: create-site count != 2"
    assert breakdown.get("page-import") == 1, "FAIL: page-import count != 1"

    print("  ✓ all trace tags match expectations")

    synth_path.unlink()


def main() -> None:
    print(f"Skill tracker self-test\n  hook: {HOOK}\n  builtins filtered: {sorted(BUILTIN_COMMANDS)[:6]}...\n")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, prefix="parser_synth_"
    ) as tf:
        synth_path = Path(tf.name)
    build_synthetic_transcript(synth_path)
    try:
        test_parser(synth_path)
    finally:
        synth_path.unlink()

    test_hook_against_real_trace()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
