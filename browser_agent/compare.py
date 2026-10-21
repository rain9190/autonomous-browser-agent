"""Paired one-shot versus iterative evaluation; no recovery or injected errors."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from uuid import uuid4

from .budget import Budget
from .metrics import COMPLETION_METRIC, full_credit_success, positive_reward_terminal, valid_reward
from .comparison_worker import MODEL
from .evaluate import ROOT, TASKS

ARMS = ("oneshot", "iterative")
STOP_REASONS = {"api_error", "connection_error", "timeout", "configuration_error",
                "environment_error", "cleanup_error", "invalid_report", "agent_error", "interrupted"}


def invalid(arm, task, seed, max_steps, reason="invalid_report"):
    return {"arm": arm, "task": task, "seed": seed, "max_steps": max_steps,
            "model": MODEL, "success": False, "reason": reason,
            "api_calls": None, "input_tokens": None, "output_tokens": None,
            "steps": None, "duration_seconds": None,
            "api_usage_may_be_incomplete": True, "initial_observation_sha256": None}


def parse_arm(stdout, returncode, arm, task, seed, max_steps):
    try:
        r = json.loads(stdout)
        if not isinstance(r, dict):
            raise ValueError()
        for k, v in {"arm": arm, "task": task, "seed": seed, "model": MODEL,
                     "max_steps": max_steps, "max_recoveries": 0}.items():
            if r.get(k) != v:
                raise ValueError()
        if type(r.get("success")) is not bool or type(r.get("api_usage_may_be_incomplete")) is not bool:
            raise ValueError()
        for k in ("steps", "api_calls", "input_tokens", "output_tokens"):
            if type(r.get(k)) is not int or r[k] < 0:
                raise ValueError()
        if r["steps"] > max_steps or r["api_calls"] > (1 if arm == "oneshot" else max_steps):
            raise ValueError()
        if not isinstance(r.get("duration_seconds"), (int, float)) or not math.isfinite(r["duration_seconds"]) or r["duration_seconds"] < 0:
            raise ValueError()
        reason = r.get("reason")
        allowed = STOP_REASONS | {"benchmark_success", "invalid_model_action_or_plan", "plan_exhausted",
            "planned_target_invalid", "observation_budget_exhausted", "browser_action_error",
            "episode_ended_without_success", "step_budget_exhausted", "partial_credit_terminal"}
        if reason not in allowed:
            raise ValueError()
        digest = r.get("initial_observation_sha256")
        if reason not in STOP_REASONS and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError()
        if not valid_reward(r.get("reward")):
            raise ValueError()
        if r.get("completion_metric", COMPLETION_METRIC) != COMPLETION_METRIC:
            raise ValueError()
        positive = positive_reward_terminal(r["reward"], r.get("terminated"), r.get("truncated"), reason == "browser_action_error")
        if "positive_reward_terminal" in r and (type(r["positive_reward_terminal"]) is not bool or r["positive_reward_terminal"] != positive):
            raise ValueError()
        success = (reason == "benchmark_success" and returncode == 0
                   and full_credit_success(r["reward"], r.get("terminated"), r.get("truncated")))
        if r["success"] != success or (not success and returncode != 1):
            raise ValueError()
        keys = ("arm", "task", "seed", "model", "max_steps", "max_recoveries", "success",
                "reason", "steps", "api_calls", "input_tokens", "output_tokens",
                "api_usage_may_be_incomplete", "duration_seconds", "initial_observation_sha256")
        result = {k: r[k] for k in keys}
        result.update(reward=r["reward"], positive_reward_terminal=positive,
                      completion_metric=r.get("completion_metric", "legacy_unversioned"))
        if type(r.get("http_status")) is int:
            result["http_status"] = r["http_status"]
        return result
    except (ValueError, TypeError, KeyError):
        return invalid(arm, task, seed, max_steps)


def run_arm(arm, task, seed, max_steps):
    process = subprocess.Popen(
        [sys.executable, "-m", "browser_agent.comparison_worker", "--arm", arm,
         "--task", task, "--seed", str(seed), "--max-steps", str(max_steps)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=Budget(max_steps).run_timeout + 10)
        return parse_arm(stdout, process.returncode, arm, task, seed, max_steps)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if sys.exc_info()[0] is KeyboardInterrupt:
            raise
        return invalid(arm, task, seed, max_steps, "timeout")


def summarize_pairs(pairs, planned, max_steps):
    matched = [p for p in pairs if p["matched"]]
    all_records = [r for p in pairs for r in p["arms"].values()]
    per_arm = {}
    for arm in ARMS:
        rows = [p["arms"][arm] for p in matched]
        means = {}
        for k in ("steps", "api_calls", "duration_seconds", "input_tokens", "output_tokens"):
            values = [r[k] for r in rows if r[k] is not None]
            means["mean_" + k] = sum(values) / len(values) if values else None
        per_arm[arm] = {"partial_credit_episodes": sum(r.get("positive_reward_terminal", False) and valid_reward(r.get("reward")) and r["reward"] < 1 - 1e-9 for r in rows),
                        "matched_episodes": len(rows), "successes": sum(r["success"] for r in rows),
                        "success_rate": sum(r["success"] for r in rows) / len(rows) if rows else None,
                        "episodes_with_potentially_incomplete_usage": sum(r["api_usage_may_be_incomplete"] for r in rows),
                        "failure_reasons": {reason: sum(r["reason"] == reason for r in rows)
                                            for reason in sorted({r["reason"] for r in rows if not r["success"]})},
                        **means}
    counts = {"both_succeeded": 0, "both_failed": 0, "oneshot_only": 0, "iterative_only": 0}
    for pair in matched:
        a, b = (pair["arms"][arm]["success"] for arm in ARMS)
        key = "both_succeeded" if a and b else "oneshot_only" if a else "iterative_only" if b else "both_failed"
        counts[key] += 1
    return {"evaluation_mode": "paired_oneshot_vs_iterative", "completion_metric": COMPLETION_METRIC, "planned_pairs": planned,
            "attempted_pairs": len(pairs), "matched_pairs": len(matched),
            "unmatched_or_incomplete_pairs": len(pairs) - len(matched),
            "unattempted_pairs": planned - len(pairs),
            "complete": len(pairs) == planned and len(matched) == planned,
            "model": MODEL, "max_steps_per_arm": max_steps, "max_recoveries": 0,
            "api_call_ceiling": planned * (max_steps + 1),
            "reported_api_calls": sum(r["api_calls"] or 0 for r in all_records),
            "reported_input_tokens": sum(r["input_tokens"] or 0 for r in all_records),
            "reported_output_tokens": sum(r["output_tokens"] or 0 for r in all_records),
            "episodes_with_unknown_or_incomplete_usage": sum(r["api_usage_may_be_incomplete"] for r in all_records),
            "paired_outcomes": counts, "per_arm_on_matched_pairs": per_arm}


def run_comparison(tasks, seeds, max_steps, output, runner=run_arm, *,
                   arms=ARMS, calls_per_pair=None, summary_builder=summarize_pairs,
                   config_extra=None, pair_validator=None):
    Budget(max_steps)
    calls_per_pair = max_steps + 1 if calls_per_pair is None else calls_per_pair
    cases = [(t, s) for t in tasks for s in seeds]
    if not cases or len(cases) != len(set(cases)) or any(t not in TASKS for t in tasks):
        raise ValueError("Choose distinct allowlisted task/seed pairs")
    if len(cases) * calls_per_pair > 24:
        raise ValueError("Comparison exceeds the 24-call ceiling")
    output.mkdir(parents=True, exist_ok=False)
    config = {"completion_metric": COMPLETION_METRIC, "tasks": tasks, "seeds": seeds, "max_steps": max_steps, "model": MODEL,
              "max_recoveries": 0, "arm_order": "alternates by pair; starts oneshot",
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((ROOT / "browser_agent").glob("*.py"))},
              "package_versions": {p: importlib.metadata.version(p) for p in
                                   ("openai", "langgraph", "pydantic", "browsergym-core", "browsergym-miniwob")}}
    config.update(arms=list(arms), planned_api_call_ceiling=len(cases) * calls_per_pair)
    config["arm_order"] = f"alternates by pair; starts {arms[0]}"
    config.update(config_extra or {})
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    pairs = []
    interrupted = False
    try:
        for index, (task, seed) in enumerate(cases):
            pair = {"task": task, "seed": seed, "matched": False, "arms": {}}
            pairs.append(pair)
            order = arms if index % 2 == 0 else tuple(reversed(arms))
            for arm in order:
                print(f"[{index + 1}/{len(cases)}] {task}, seed {seed}, {arm}", flush=True)
                record = runner(arm, task, seed, max_steps)
                pair["arms"][arm] = record
                (output / f"{index + 1:02d}-{task}-seed{seed}-{arm}.json").write_text(json.dumps(record, indent=2) + "\n")
                print(f"  {record['reason']}", flush=True)
                if record["reason"] in STOP_REASONS:
                    break
            if len(pair["arms"]) == 2:
                left, right = (pair["arms"][a] for a in arms)
                pair["matched"] = (left["initial_observation_sha256"] is not None
                    and left["initial_observation_sha256"] == right["initial_observation_sha256"]
                    and left.get("completion_metric", "legacy_unversioned") == right.get("completion_metric", "legacy_unversioned")
                    and all(r["reason"] not in STOP_REASONS for r in (left, right)))
                if pair["matched"] and pair_validator is not None:
                    pair["matched"] = pair_validator(left, right)
                if not pair["matched"]:
                    pair["exclusion_reason"] = "pair_matching_or_infrastructure_error"
            if any(r["reason"] in STOP_REASONS for r in pair["arms"].values()):
                break
    except KeyboardInterrupt:
        interrupted = True
        if pairs and arm not in pairs[-1]["arms"]:
            record = invalid(arm, task, seed, max_steps, "interrupted")
            pairs[-1]["arms"][arm] = record
            (output / f"{index + 1:02d}-{task}-seed{seed}-{arm}.json").write_text(
                json.dumps(record, indent=2) + "\n")
    finally:
        summary = summary_builder(pairs, len(cases), max_steps)
        summary["interrupted"] = interrupted
        (output / "pairs.json").write_text(json.dumps(pairs, indent=2) + "\n")
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", choices=TASKS, nargs="+", default=["enter-text", "click-button-sequence"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 29])
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=2)
    args = parser.parse_args()
    if len(set(args.tasks)) != len(args.tasks) or len(set(args.seeds)) != len(args.seeds):
        parser.error("Tasks and seeds must be unique")
    if len(args.tasks) * len(args.seeds) * (args.max_steps + 1) > 24:
        parser.error("Comparison exceeds the 24-call ceiling")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / f"comparison-{stamp}-{uuid4().hex[:8]}"
    summary = run_comparison(args.tasks, args.seeds, args.max_steps, output)
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")
    # A complete experiment may legitimately contain failed tasks in either arm.
    return 0 if summary["complete"] and not summary["interrupted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
