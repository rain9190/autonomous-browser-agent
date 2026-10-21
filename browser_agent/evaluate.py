"""Run a small, serial evaluation; never read potentially stale episode files."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4

from .budget import Budget
from .metrics import COMPLETION_METRIC, full_credit_success, positive_reward_terminal, valid_reward

TASKS = ("click-test", "click-button", "click-button-sequence", "enter-text", "login-user", "click-checkboxes-soft", "click-option", "choose-list", "click-tab", "click-collapsible", "click-link", "click-collapsible-2", "click-tab-2-easy", "click-tab-2-medium", "enter-text-2", "click-test-2", "click-test-transfer", "click-dialog", "click-dialog-2")
ROOT = Path(__file__).resolve().parents[1]
MAX_EPISODES = 12


def parse_result(stdout, returncode, task, seed, max_steps=2):
    result = None
    try:
        result = json.loads(stdout)
        if isinstance(result, dict) and result.get("simulated_failure_requested", False):
            raise ValueError()
        if not isinstance(result, dict):
            raise ValueError()
        if result.get("task") != task or result.get("seed") != seed:
            raise ValueError()
        if type(result.get("success")) is not bool:
            raise ValueError()
        for key in ("api_calls", "steps", "input_tokens", "output_tokens"):
            if type(result.get(key)) is not int or result[key] < 0:
                raise ValueError()
        if result["api_calls"] > max_steps or result["steps"] > max_steps:
            raise ValueError()
        if not valid_reward(result.get("reward")):
            raise ValueError()
        if result.get("completion_metric", COMPLETION_METRIC) != COMPLETION_METRIC:
            raise ValueError()
        positive = positive_reward_terminal(result["reward"], result.get("terminated"), result.get("truncated"),
                                            result.get("reason") == "browser_action_error")
        if "positive_reward_terminal" in result and (type(result["positive_reward_terminal"]) is not bool or result["positive_reward_terminal"] != positive):
            raise ValueError()
        success = (result["success"] and returncode == 0
                   and result.get("reason") == "benchmark_success"
                   and full_credit_success(result["reward"], result.get("terminated"), result.get("truncated")))
        if result["success"] != success:
            raise ValueError()
        # Keep only known public result fields; never persist raw logs.
        return {"task": task, "seed": seed, "success": success,
                "status": "success" if success else "benchmark_failure",
                "reward": result["reward"], "positive_reward_terminal": positive,
                "completion_metric": result.get("completion_metric", "legacy_unversioned"),
                **{key: result[key] for key in
                   ("api_calls", "steps", "input_tokens", "output_tokens")}}
    except (ValueError, TypeError, KeyError):
        status = "invalid_report"
        if (isinstance(result, dict) and result.get("status") == "run_failed"
                and result.get("task") == task and result.get("seed") == seed):
            status = "timeout" if result.get("category") == "run_timeout" else "agent_validation_or_run_error"
        if "API request failed (HTTP 429)" in stdout:
            status = "api_quota_or_rate_limit"
        elif "API request failed (HTTP" in stdout:
            status = "api_error"
        elif "API connection failed" in stdout:
            status = "connection_error"
        elif "Run stopped safely: TimeoutError" in stdout:
            status = "timeout"
        elif "Missing OPENAI_API_KEY" in stdout or "task HTML missing" in stdout:
            status = "configuration_error"
        return {"task": task, "seed": seed, "success": False,
                "status": status, "api_calls": None,
                "input_tokens": None, "output_tokens": None}


def run_episode(task, seed, max_steps=2):
    budget = Budget(max_steps)
    start = time.monotonic()
    command = [sys.executable, "-m", "browser_agent", "--task", task, "--seed", str(seed)]
    if max_steps != 2:
        command += ["--max-steps", str(max_steps)]
    process = subprocess.Popen(
        command,
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    try:
        stdout, _ = process.communicate(timeout=budget.run_timeout + 10)
        result = parse_result(stdout, process.returncode, task, seed, max_steps)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if sys.exc_info()[0] is KeyboardInterrupt:
            raise
        result = {"task": task, "seed": seed, "success": False,
                  "status": "timeout", "api_calls": None,
                  "input_tokens": None, "output_tokens": None}
    result["duration_seconds"] = round(time.monotonic() - start, 2)
    return result


def summarize(records, planned, max_steps=2):
    successes = sum(r["success"] for r in records)
    by_task = {}
    for task in dict.fromkeys(r["task"] for r in records):
        rows = [r for r in records if r["task"] == task]
        won = sum(r["success"] for r in rows)
        by_task[task] = {"attempted": len(rows), "successes": won,
                         "success_rate": won / len(rows)}
    return {
        "evaluation_mode": "baseline",
        "completion_metric": COMPLETION_METRIC,
        "positive_reward_terminal_episodes": sum(r.get("positive_reward_terminal", False) for r in records),
        "partial_credit_episodes": sum(r.get("positive_reward_terminal", False) and valid_reward(r.get("reward")) and r["reward"] < 1 - 1e-9 for r in records),
        "planned": planned, "attempted": len(records),
        "unattempted": planned - len(records),
        "complete": len(records) == planned,
        "successes": successes,
        "success_rate_on_attempted": successes / len(records) if records else None,
        "max_steps_per_episode": max_steps,
        "api_call_ceiling": planned * max_steps,
        "reported_api_calls": sum(r["api_calls"] or 0 for r in records),
        "episodes_with_unknown_api_usage": sum(r["api_calls"] is None for r in records),
        "reported_input_tokens": sum(r["input_tokens"] or 0 for r in records),
        "reported_output_tokens": sum(r["output_tokens"] or 0 for r in records),
        "by_task": by_task,
    }


def run_suite(tasks, seeds, output, runner=run_episode, max_steps=2, summary_builder=summarize):
    Budget(max_steps)
    pairs = [(task, seed) for task in tasks for seed in seeds]
    if not pairs or len(pairs) > MAX_EPISODES or len(set(pairs)) != len(pairs):
        raise ValueError("Choose 1–12 distinct task/seed pairs")
    if len(pairs) * max_steps > 24:
        raise ValueError("Evaluation exceeds the 24-call ceiling")
    if any(task not in TASKS for task in tasks):
        raise ValueError("Task is not allowlisted")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    interrupted = False
    try:
        for index, (task, seed) in enumerate(pairs, 1):
            print(f"[{index}/{len(pairs)}] {task}, seed {seed}", flush=True)
            result = runner(task, seed) if max_steps == 2 else runner(task, seed, max_steps=max_steps)
            records.append(result)
            (output / f"{index:02d}-{task}-seed{seed}.json").write_text(
                json.dumps(result, indent=2) + "\n")
            print(f"  {result['status']}", flush=True)
            # Benchmark failures are data; infrastructure errors stop spending.
            if result["status"] not in ("success", "benchmark_failure"):
                break
    except KeyboardInterrupt:
        interrupted = True
    finally:
        summary = summary_builder(records, len(pairs), max_steps)
        summary["interrupted"] = interrupted
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="+", choices=TASKS, default=list(TASKS[:3]))
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 123])
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=2)
    args = parser.parse_args()
    if len(args.tasks) * len(args.seeds) * args.max_steps > 24:
        parser.error("Evaluation exceeds the 24-call ceiling")
    if len(args.tasks) * len(args.seeds) > MAX_EPISODES:
        parser.error("At most 12 episodes are allowed")
    if len(set(args.tasks)) != len(args.tasks) or len(set(args.seeds)) != len(args.seeds):
        parser.error("Tasks and seeds must be unique")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / f"eval-{stamp}-{uuid4().hex[:8]}"
    summary = run_suite(args.tasks, args.seeds, output, max_steps=args.max_steps)
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")
    return 0 if summary["complete"] and summary["successes"] == summary["attempted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
