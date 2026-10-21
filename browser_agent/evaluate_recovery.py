"""Evaluate injected fill-failure recovery separately from baseline results."""
import argparse
from functools import partial
from datetime import datetime, timezone
import json
import os
import signal
import subprocess
import sys
import time
from uuid import uuid4

from .budget import Budget

def scenario_mode(scenario):
    return {"python_exception": "simulated_fill_recovery",
            "disabled_textbox_timeout": "controlled_browser_timeout_recovery",
            "changed_textbox_id": "controlled_changed_id_recovery"}[scenario]

from .evaluate import ROOT, parse_result, run_suite, summarize


def parse_recovery_result(stdout, returncode, task, seed, max_steps, scenario="python_exception"):
    mode = scenario_mode(scenario)
    try:
        raw = json.loads(stdout)
        if not isinstance(raw, dict):
            raise ValueError()
        if raw.get("simulated_failure_requested") is not True or raw.get("simulated_failure_injected") is not True:
            raise ValueError()
        if raw.get("controlled_failure_scenario", "python_exception") != scenario:
            raise ValueError()
        if raw.get("max_recoveries") != 1 or raw.get("max_steps") != max_steps:
            raise ValueError()
        used = raw.get("recoveries_used")
        if type(used) is not int or not 0 <= used <= 1:
            raise ValueError()
        rows = raw.get("progress")
        if not isinstance(rows, list) or len(rows) != raw.get("steps"):
            raise ValueError()
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict) or row.get("step") != index:
                raise ValueError()
            if row.get("action") not in ("click", "fill") or type(row.get("execution_ok")) is not bool:
                raise ValueError()
        # The simulator fails the first fill, before any page mutation.
        failed = [i for i, row in enumerate(rows) if not row["execution_ok"]]
        if not failed or rows[failed[0]]["action"] != "fill":
            raise ValueError()
        if scenario in ("disabled_textbox_timeout", "changed_textbox_id") and (
            raw.get("controlled_timeout_confirmed") is not True
            or rows[failed[0]].get("error_kind") != "playwright_fill_timeout"
        ):
            raise ValueError()
        if scenario == "changed_textbox_id":
            first_failure = rows[failed[0]]
            changed = (raw.get("changed_id_confirmed") is True
                       and first_failure.get("failed_fill_target_absent") is True)
            fresh = any(row["action"] == "fill" and row["execution_ok"]
                        and row.get("bid") and row.get("bid") != first_failure.get("bid")
                        for row in rows[failed[0] + 1:])
            if not changed or (raw.get("success") and (not fresh or raw.get("fresh_id_recovery_confirmed") is not True)):
                raise ValueError()
        if used and failed[0] == len(rows) - 1:
            raise ValueError()
        if raw.get("success") and (used != 1 or len(failed) != 1):
            raise ValueError()
        cleaned = dict(raw)
        cleaned["simulated_failure_requested"] = False
        result = parse_result(json.dumps(cleaned), returncode, task, seed, max_steps)
        if result["status"] == "invalid_report":
            raise ValueError()
        result.update(evaluation_mode=mode, controlled_failure_scenario=scenario,
                      browser_timeout_confirmed=scenario in ("disabled_textbox_timeout", "changed_textbox_id"),
                      changed_id_confirmed=scenario == "changed_textbox_id",
                      fresh_id_recovery_confirmed=bool(scenario == "changed_textbox_id" and raw.get("fresh_id_recovery_confirmed")),
                      injection_confirmed=True, recoveries_used=used,
                      recovered_success=result["success"] and used == 1)
        return result
    except (ValueError, TypeError, KeyError):
        # Shared classifier supplies safe status metadata for transport/API errors.
        result = parse_result(stdout, returncode, task, seed, max_steps)
        if result["status"] in ("success", "benchmark_failure"):
            result = {"task": task, "seed": seed, "success": False,
                      "status": "invalid_report", "api_calls": None,
                      "input_tokens": None, "output_tokens": None}
        result.update(evaluation_mode=mode, controlled_failure_scenario=scenario,
                      browser_timeout_confirmed=False,
                      injection_confirmed=False, recoveries_used=None,
                      recovered_success=False)
        return result


def run_recovery_episode(task, seed, max_steps=3, scenario="python_exception"):
    if scenario not in ("python_exception", "disabled_textbox_timeout", "changed_textbox_id"):
        raise ValueError("Unknown controlled failure scenario")
    mode = scenario_mode(scenario)
    if task not in ("enter-text", "login-user"):
        raise ValueError("Recovery evaluation requires a local text-entry task")
    budget = Budget(max_steps)
    command = [sys.executable, "-m", "browser_agent", "--task", task,
               "--seed", str(seed), "--max-steps", str(max_steps),
               "--max-recoveries", "1",
               {"disabled_textbox_timeout": "--disabled-textbox-timeout-once",
                "changed_textbox_id": "--changed-textbox-id-once",
                "python_exception": "--simulate-fill-error-once"}[scenario]]
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=budget.run_timeout + 10)
        result = parse_recovery_result(stdout, process.returncode, task, seed, max_steps, scenario)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if sys.exc_info()[0] is KeyboardInterrupt:
            raise
        result = {"task": task, "seed": seed, "success": False, "status": "timeout",
                  "api_calls": None, "input_tokens": None, "output_tokens": None,
                  "evaluation_mode": mode, "controlled_failure_scenario": scenario,
                  "browser_timeout_confirmed": False, "injection_confirmed": False,
                  "recoveries_used": None, "recovered_success": False}
    result["duration_seconds"] = round(time.monotonic() - start, 2)
    return result


def recovery_summary(records, planned, max_steps, scenario="python_exception"):
    summary = summarize(records, planned, max_steps)
    injected = sum(r.get("injection_confirmed", False) for r in records)
    recovered = sum(r.get("recovered_success", False) for r in records)
    summary.update(
        evaluation_mode=(scenario_mode(scenario)),
        controlled_failure_scenario=scenario,
        confirmed_changed_id_episodes=sum(r.get("changed_id_confirmed", False) for r in records),
        fresh_id_recovered_episodes=sum(r.get("fresh_id_recovery_confirmed", False) and r.get("recovered_success", False) for r in records),
        confirmed_browser_timeout_episodes=sum(r.get("browser_timeout_confirmed", False) for r in records),
        max_recoveries_per_episode=1,
        confirmed_injected_episodes=injected, recovered_episodes=recovered,
        recovery_success_rate_on_attempted=recovered / len(records) if records else None,
        recovery_success_rate_on_confirmed_injections=recovered / injected if injected else None,
        recoveries_used=sum(r.get("recoveries_used") or 0 for r in records),
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("enter-text", "login-user"), default="enter-text")
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 42, 123])
    parser.add_argument("--max-steps", type=int, choices=range(3, 7), default=3)
    parser.add_argument("--scenario", choices=("python_exception", "disabled_textbox_timeout", "changed_textbox_id"), default="python_exception")
    args = parser.parse_args()
    if len(args.seeds) != len(set(args.seeds)):
        parser.error("Seeds must be unique")
    if len(args.seeds) * args.max_steps > 24:
        parser.error("Evaluation exceeds the 24-call ceiling")
    if args.task == "login-user" and args.max_steps < 4:
        parser.error("login-user with an injected failure requires at least four steps")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = {"python_exception": "recovery-eval", "disabled_textbox_timeout": "browser-timeout-eval",
              "changed_textbox_id": "changed-id-eval"}[args.scenario]
    output = ROOT / "results" / f"{prefix}-{stamp}-{uuid4().hex[:8]}"
    summary = run_suite([args.task], args.seeds, output,
                        runner=partial(run_recovery_episode, scenario=args.scenario), max_steps=args.max_steps,
                        summary_builder=partial(recovery_summary, scenario=args.scenario))
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")
    return 0 if summary["complete"] and summary["recovered_episodes"] == summary["planned"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
