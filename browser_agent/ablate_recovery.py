"""Paired iterative-agent ablation: identical controlled failure, recovery off/on."""
import argparse
from datetime import datetime, timezone
from functools import partial
import json
import os
import re
import signal
import subprocess
import sys
from uuid import uuid4

from .budget import Budget
from .compare import invalid, parse_arm, run_comparison, summarize_pairs
from .evaluate import ROOT

ARMS = ("recovery_off", "recovery_on")
SCENARIOS = ("disabled_textbox_timeout", "changed_textbox_id")


def parse_ablation(stdout, returncode, arm, task, seed, max_steps, scenario):
    try:
        raw = json.loads(stdout)
        if not isinstance(raw, dict) or raw.get("arm") != arm or raw.get("controlled_failure_scenario") != scenario:
            raise ValueError()
        allowance = int(arm == "recovery_on")
        if type(raw.get("max_recoveries")) is not int or raw["max_recoveries"] != allowance:
            raise ValueError()
        used = raw.get("recoveries_used")
        if type(used) is not int or not 0 <= used <= allowance:
            raise ValueError()
        confirmed = raw.get("failure_injection_confirmed")
        if type(confirmed) is not bool:
            raise ValueError()
        signature = raw.get("injected_failure_signature")
        if confirmed and (not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature)):
            raise ValueError()
        if raw.get("success") and confirmed and (arm == "recovery_off" or used != 1):
            raise ValueError()
        # Reuse common model/budget/status validation without weakening it.
        normalized = {**raw, "arm": "iterative", "max_recoveries": 0}
        result = parse_arm(json.dumps(normalized), returncode, "iterative", task, seed, max_steps)
        result.update(arm=arm, max_recoveries=allowance, recoveries_used=used,
                      controlled_failure_scenario=scenario, failure_injection_confirmed=confirmed,
                      injected_failure_signature=signature)
        return result
    except (ValueError, TypeError, KeyError):
        return invalid(arm, task, seed, max_steps)


def matching_failures(left, right):
    return (left.get("failure_injection_confirmed") is True
            and right.get("failure_injection_confirmed") is True
            and left.get("injected_failure_signature") is not None
            and left.get("injected_failure_signature") == right.get("injected_failure_signature"))


def run_arm(arm, task, seed, max_steps, scenario):
    process = subprocess.Popen(
        [sys.executable, "-m", "browser_agent.comparison_worker", "--arm", arm,
         "--task", task, "--seed", str(seed), "--max-steps", str(max_steps), "--scenario", scenario],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=Budget(max_steps).run_timeout + 10)
        return parse_ablation(stdout, process.returncode, arm, task, seed, max_steps, scenario)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if sys.exc_info()[0] is KeyboardInterrupt:
            raise
        return invalid(arm, task, seed, max_steps, "timeout")


def summarize(pairs, planned, max_steps, scenario):
    # Share arithmetic while publishing the correct experimental arm names.
    translated = [{**p, "arms": {("oneshot" if a == "recovery_off" else "iterative"): r
                                 for a, r in p["arms"].items()}} for p in pairs]
    result = summarize_pairs(translated, planned, max_steps)
    old_arms = result.pop("per_arm_on_matched_pairs")
    off, on = old_arms["oneshot"], old_arms["iterative"]
    old_counts = result.pop("paired_outcomes")
    result.update(evaluation_mode="paired_recovery_ablation", controlled_failure_scenario=scenario,
        max_recoveries={"recovery_off": 0, "recovery_on": 1},
        api_call_ceiling=planned * 2 * max_steps,
        per_arm_on_matched_pairs={"recovery_off": off, "recovery_on": on},
        paired_outcomes={"both_succeeded": old_counts["both_succeeded"],
                        "both_failed": old_counts["both_failed"],
                        "recovery_off_only": old_counts["oneshot_only"],
                        "recovery_on_only": old_counts["iterative_only"]},
        success_rate_difference_percentage_points=(100 * (on["success_rate"] - off["success_rate"])
            if on["success_rate"] is not None else None),
        mean_additional_api_calls=(on["mean_api_calls"] - off["mean_api_calls"]
            if on["mean_api_calls"] is not None else None),
        mean_additional_duration_seconds=(on["mean_duration_seconds"] - off["mean_duration_seconds"]
            if on["mean_duration_seconds"] is not None else None),
    )
    return result


def run_ablation(task, seeds, max_steps, scenario, output, runner=None):
    if task not in ("enter-text", "login-user") or scenario not in SCENARIOS:
        raise ValueError("Choose an allowlisted text task and controlled scenario")
    if max_steps < (3 if task == "enter-text" else 4):
        raise ValueError("Budget must permit completing the task after one failed fill")
    return run_comparison([task], seeds, max_steps, output,
        runner=runner or partial(run_arm, scenario=scenario), arms=ARMS,
        calls_per_pair=2 * max_steps, summary_builder=partial(summarize, scenario=scenario),
        pair_validator=matching_failures,
        config_extra={"evaluation_mode": "paired_recovery_ablation", "controlled_failure_scenario": scenario,
                      "max_recoveries": {"recovery_off": 0, "recovery_on": 1},
                      "matching_rule": "initial observation AND first fill target/error/post-failure observation hashes match"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("enter-text", "login-user"), default="enter-text")
    parser.add_argument("--seeds", type=int, nargs="+", default=[31, 47])
    parser.add_argument("--max-steps", type=int, choices=range(3, 7), default=3)
    parser.add_argument("--scenario", choices=SCENARIOS, default="disabled_textbox_timeout")
    args = parser.parse_args()
    if len(args.seeds) != len(set(args.seeds)) or len(args.seeds) * 2 * args.max_steps > 24:
        parser.error("Choose unique seeds within the 24-call ceiling")
    if args.task == "login-user" and args.max_steps < 4:
        parser.error("Login with one failed fill requires at least four actions")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / f"recovery-ablation-{stamp}-{uuid4().hex[:8]}"
    summary = run_ablation(args.task, args.seeds, args.max_steps, args.scenario, output)
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")
    return 0 if summary["complete"] and not summary["interrupted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
