"""Run the one-shot comparison system on a local allowlisted MiniWoB task."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from uuid import uuid4

import gymnasium as gym
import browsergym.miniwob  # noqa: F401
from browsergym.utils.obs import flatten_axtree_to_str
from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError

from .actions import action_mapping
from .budget import Budget
from .observations import enrich_benchmark_links
from .metrics import COMPLETION_METRIC
from .evaluate import TASKS
from .oneshot import OneShotAdapter, execute_plan

ROOT = Path(__file__).resolve().parents[1]


def deadline(*_):
    raise TimeoutError("Run exceeded time budget")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=TASKS, default="enter-text")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--max-steps", type=int, choices=range(1, 8), default=2)
    args = parser.parse_args()
    budget = Budget(args.max_steps)
    load_dotenv(ROOT / ".env.local", override=False)
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("Missing OPENAI_API_KEY in environment or .env.local")
        return 1
    html = ROOT / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    if not (html / (args.task + ".html")).is_file():
        print("Requested MiniWoB task HTML missing from vendor checkout")
        return 1
    report = {"evaluation_mode": "oneshot", "completion_metric": COMPLETION_METRIC,
              "positive_reward_terminal": False, "task": args.task, "seed": args.seed,
              "max_steps": args.max_steps, "success": False, "steps": 0,
              "reason": "run_error", "reward": 0.0, "terminated": False, "truncated": False}
    env = model = None
    started = time.monotonic()
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(budget.run_timeout)
    try:
        model = OneShotAdapter(os.environ["OPENAI_API_KEY"], max_steps=args.max_steps)
        env = gym.make(f"browsergym/miniwob.{args.task}", headless=True,
                       action_mapping=action_mapping,
                       task_kwargs={"base_url": html.as_uri() + "/",
                                    "episode_max_time": budget.run_timeout * 1000})
        observation, _ = env.reset(seed=args.seed)
        tree = enrich_benchmark_links(env, flatten_axtree_to_str(observation["axtree_object"]))
        initial = json.dumps({"goal": observation["goal"], "tree": tree}, sort_keys=True)
        report["initial_observation_sha256"] = hashlib.sha256(initial.encode()).hexdigest()
        plan = model.plan(observation["goal"], tree)
        report.update(execute_plan(env, observation, plan, args.max_steps))
    except APIStatusError as exc:
        report.update(reason="api_error", http_status=exc.status_code)
    except APIConnectionError:
        report["reason"] = "connection_error"
    except Exception as exc:
        report.update(reason="run_error", error_type=type(exc).__name__)
    finally:
        try:
            if env is not None:
                env.close()
        finally:
            if model is not None:
                model.close()
            signal.alarm(0)
    report.update(model=model.model if model else None,
                  api_calls=model.calls if model else 0,
                  input_tokens=model.input_tokens if model else 0,
                  output_tokens=model.output_tokens if model else 0,
                  api_usage_may_be_incomplete=report["reason"] in ("api_error", "connection_error", "run_error"),
                  duration_seconds=round(time.monotonic() - started, 2))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / f"oneshot-{args.task}-seed{args.seed}-{stamp}-{uuid4().hex[:8]}.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
