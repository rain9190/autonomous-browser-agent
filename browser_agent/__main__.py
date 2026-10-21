import argparse
import json
import os
from pathlib import Path
import signal
from datetime import datetime, timezone
from uuid import uuid4

import gymnasium as gym
import browsergym.miniwob  # noqa: F401: register task
from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError

from .actions import action_mapping
from .budget import Budget
from .model import ModelAdapter
from .recovery import FillFailureOnce, DisabledTextboxOnce, ChangedTextboxIdOnce
from .workflow import build_workflow
from .diagnostics import describe_error

ROOT = Path(__file__).resolve().parents[1]


def deadline(*_):
    raise TimeoutError("Run exceeded time budget")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["click-test", "click-button", "click-button-sequence", "enter-text", "login-user", "click-checkboxes-soft", "click-option", "choose-list"], default="click-test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=2)
    parser.add_argument("--max-recoveries", type=int, choices=range(0, 3), default=0)
    scenarios = parser.add_mutually_exclusive_group()
    scenarios.add_argument("--simulate-fill-error-once", action="store_true")
    scenarios.add_argument("--disabled-textbox-timeout-once", action="store_true")
    scenarios.add_argument("--changed-textbox-id-once", action="store_true")
    args = parser.parse_args()
    failure_requested = args.simulate_fill_error_once or args.disabled_textbox_timeout_once or args.changed_textbox_id_once
    scenario = ("changed_textbox_id" if args.changed_textbox_id_once else
                "disabled_textbox_timeout" if args.disabled_textbox_timeout_once else
                "python_exception" if args.simulate_fill_error_once else "none")
    if failure_requested and args.task not in ("enter-text", "login-user"):
        parser.error("Fill-error simulation requires enter-text or login-user")
    budget = Budget(args.max_steps)
    load_dotenv(ROOT / ".env.local", override=False)
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("Missing OPENAI_API_KEY in environment or .env.local")
        return 1
    html = ROOT / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    if not (html / (args.task + ".html")).is_file():
        print("Requested MiniWoB task HTML missing from vendor checkout")
        return 1
    # Always use the existing local benchmark, rather than an arbitrary URL.
    base_url = html.as_uri() + "/"
    env = model = None
    phase = "setup"
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(budget.run_timeout)
    try:
        model = ModelAdapter(key, max_steps=budget.max_steps)
        mapping = (ChangedTextboxIdOnce() if args.changed_textbox_id_once else
                   DisabledTextboxOnce() if args.disabled_textbox_timeout_once else
                   FillFailureOnce() if args.simulate_fill_error_once else action_mapping)
        env = gym.make(
            f"browsergym/miniwob.{args.task}", headless=True,
            action_mapping=mapping,
            task_kwargs={"base_url": base_url, "episode_max_time": budget.run_timeout * 1000},
        )
        observation, _ = env.reset(seed=args.seed)
        phase = "agent_workflow"
        state = build_workflow(env, model, max_steps=budget.max_steps, max_recoveries=args.max_recoveries).invoke(
            {"observation": observation, "steps": 0}, {"recursion_limit": 5 * budget.max_steps + 2}
        )
        report = {k: state[k] for k in ["success", "reason", "steps", "reward", "terminated", "truncated", "trace", "history", "progress", "remaining_steps", "recoveries_used", "failed_actions", "completion_metric", "positive_reward_terminal"]}
        changed_id_confirmed = bool(args.changed_textbox_id_once and any(
            row["failed_fill_target_absent"] and row["bid"] == mapping.old_bid
            for row in state["progress"]))
        fresh_id_confirmed = bool(changed_id_confirmed and any(
            row["action"] == "fill" and row["execution_ok"] and row["bid"] != mapping.old_bid
            for row in state["progress"]))
        report.update(changed_id_confirmed=changed_id_confirmed,
                      fresh_id_recovery_confirmed=fresh_id_confirmed,
                      max_recoveries=args.max_recoveries,
                      simulated_failure_requested=failure_requested,
                      controlled_failure_scenario=scenario,
                      controlled_timeout_confirmed=bool((args.disabled_textbox_timeout_once or args.changed_textbox_id_once) and any(
                          row["error_kind"] == "playwright_fill_timeout" for row in state["progress"])),
                      simulated_failure_injected=bool(failure_requested and mapping.injected),
                      max_steps=budget.max_steps, task=args.task, seed=args.seed, model=model.model, api_calls=model.calls,
                      input_tokens=model.input_tokens, output_tokens=model.output_tokens)
        print(json.dumps(report, indent=2))
        (ROOT / "results").mkdir(exist_ok=True)
        (ROOT / f"results/day2-{args.task}-seed{args.seed}-budget{budget.max_steps}-recovery{args.max_recoveries}-sim{int(failure_requested)}-{scenario}.json").write_text(json.dumps(report, indent=2) + "\n")
        return 0 if state["success"] else 1
    except APIStatusError as exc:
        # SDK exception text can include response bodies; never log it.
        print(f"API request failed (HTTP {exc.status_code}); check API billing and model access.")
        return 1
    except APIConnectionError:
        print("API connection failed; check network access.")
        return 1
    except Exception as exc:
        report = {"status": "run_failed", "success": False, "task": args.task,
                  "seed": args.seed, "phase": phase, "max_steps": budget.max_steps,
                  "api_calls": model.calls if model else 0,
                  "api_usage_may_be_incomplete": True, **describe_error(exc)}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (ROOT / "results").mkdir(exist_ok=True)
        output = ROOT / "results" / f"failure-{args.task}-seed{args.seed}-{stamp}-{uuid4().hex[:8]}.json"
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 1
    finally:
        try:
            if env is not None:
                env.close()
        finally:
            if model is not None:
                model.close()
            signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
