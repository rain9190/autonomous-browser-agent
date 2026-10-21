import argparse
import json
import os
from pathlib import Path
import signal

import gymnasium as gym
import browsergym.miniwob  # noqa: F401: register task
from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError

from .actions import action_mapping
from .budget import Budget
from .model import ModelAdapter
from .recovery import FillFailureOnce
from .workflow import build_workflow

ROOT = Path(__file__).resolve().parents[1]


def deadline(*_):
    raise TimeoutError("Run exceeded time budget")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["click-test", "click-button", "click-button-sequence", "enter-text", "login-user"], default="click-test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=2)
    parser.add_argument("--max-recoveries", type=int, choices=range(0, 3), default=0)
    parser.add_argument("--simulate-fill-error-once", action="store_true")
    args = parser.parse_args()
    if args.simulate_fill_error_once and args.task not in ("enter-text", "login-user"):
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
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(budget.run_timeout)
    try:
        model = ModelAdapter(key, max_steps=budget.max_steps)
        mapping = FillFailureOnce() if args.simulate_fill_error_once else action_mapping
        env = gym.make(
            f"browsergym/miniwob.{args.task}", headless=True,
            action_mapping=mapping,
            task_kwargs={"base_url": base_url, "episode_max_time": budget.run_timeout * 1000},
        )
        observation, _ = env.reset(seed=args.seed)
        state = build_workflow(env, model, max_steps=budget.max_steps, max_recoveries=args.max_recoveries).invoke(
            {"observation": observation, "steps": 0}, {"recursion_limit": 5 * budget.max_steps + 2}
        )
        report = {k: state[k] for k in ["success", "reason", "steps", "reward", "terminated", "truncated", "trace", "history", "progress", "remaining_steps", "recoveries_used", "failed_actions"]}
        report.update(max_recoveries=args.max_recoveries,
                      simulated_failure_requested=args.simulate_fill_error_once,
                      simulated_failure_injected=bool(args.simulate_fill_error_once and mapping.injected),
                      max_steps=budget.max_steps, task=args.task, seed=args.seed, model=model.model, api_calls=model.calls,
                      input_tokens=model.input_tokens, output_tokens=model.output_tokens)
        print(json.dumps(report, indent=2))
        (ROOT / "results").mkdir(exist_ok=True)
        (ROOT / f"results/day2-{args.task}-seed{args.seed}-budget{budget.max_steps}-recovery{args.max_recoveries}-sim{int(args.simulate_fill_error_once)}.json").write_text(json.dumps(report, indent=2) + "\n")
        return 0 if state["success"] else 1
    except APIStatusError as exc:
        # SDK exception text can include response bodies; never log it.
        print(f"API request failed (HTTP {exc.status_code}); check API billing and model access.")
        return 1
    except APIConnectionError:
        print("API connection failed; check network access.")
        return 1
    except Exception as exc:
        print(f"Run stopped safely: {type(exc).__name__}")
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
