"""Smoke test: push a synthetic trace + run into the eds-skill-assessment-2026-05 experiment.

Proves the tracking URI, sqlite backend, and artifact store are all wired correctly
without needing the Claude Code Stop hook to fire.
"""
from __future__ import annotations
import os
import time

import mlflow

TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5050")
EXPERIMENT_NAME = os.environ.get("MLFLOW_EXPERIMENT_NAME", "eds-skill-assessment-2026-05")

mlflow.set_tracking_uri(TRACKING_URI)
mlflow.set_experiment(EXPERIMENT_NAME)


@mlflow.trace(name="smoke_trace_root")
def smoke_root() -> dict:
    return _inner_work("create-site smoke check", iters=3)


@mlflow.trace(name="inner_work")
def _inner_work(label: str, iters: int) -> dict:
    out = []
    for i in range(iters):
        out.append(_one_step(label, i))
        time.sleep(0.05)
    return {"label": label, "steps": out}


@mlflow.trace(name="one_step")
def _one_step(label: str, idx: int) -> str:
    return f"{label}#{idx}"


def main() -> None:
    with mlflow.start_run(run_name="smoke-from-script") as run:
        mlflow.log_param("source", "scripts/smoke_trace.py")
        mlflow.log_param("workspace_root", "/Users/jackjin/dev/eds-skill-assess-2026-05")
        mlflow.log_metric("smoke_metric", 1.0)
        result = smoke_root()
        mlflow.log_dict(result, "smoke_result.json")
        print(f"run_id={run.info.run_id}")
        print(f"experiment_id={run.info.experiment_id}")
        print(f"tracking_uri={TRACKING_URI}")
        print(f"UI: {TRACKING_URI}/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id}")


if __name__ == "__main__":
    main()
