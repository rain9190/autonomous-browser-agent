"""One isolated arm of a matched local benchmark comparison."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time

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
from .model import ModelAdapter
from .oneshot import OneShotAdapter, execute_plan
from .workflow import build_workflow
from .recovery import DisabledTextboxOnce, ChangedTextboxIdOnce

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-4.1-mini-2025-04-14"


def fingerprint(observation, env=None):
    tree = enrich_benchmark_links(env, flatten_axtree_to_str(observation["axtree_object"]))
    initial = json.dumps({"goal": observation["goal"], "tree": tree}, sort_keys=True)
    return hashlib.sha256(initial.encode()).hexdigest(), tree


class CountedEnv:
    def __init__(self, env):
        self.env = env
        self.steps = 0
        self.first_failure = None

    def step(self, payload):
        self.steps += 1
        result = self.env.step(payload)
        if result[0].get("last_action_error") and self.first_failure is None:
            action = json.loads(payload)
            diagnostic = str(result[0]["last_action_error"])
            self.first_failure = {"action": action["action"], "bid": action["bid"],
                "post_failure_observation_sha256": fingerprint(result[0])[0],
                "fill_timeout": diagnostic.startswith("TimeoutError:") and "Locator.fill" in diagnostic and "exceeded" in diagnostic}
        return result


def deadline(*_):
    raise TimeoutError("Run exceeded time budget")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("oneshot", "iterative", "recovery_off", "recovery_on"), required=True)
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, choices=range(1, 7), default=2)
    parser.add_argument("--scenario", choices=("none", "disabled_textbox_timeout", "changed_textbox_id"), default="none")
    args = parser.parse_args()
    ablation = args.arm in ("recovery_off", "recovery_on")
    if ablation != (args.scenario != "none"):
        parser.error("Recovery arms require a controlled scenario; comparison arms require none")
    if ablation and args.task not in ("enter-text", "login-user"):
        parser.error("Recovery ablation requires a local text-entry task")
    allowance = int(args.arm == "recovery_on")
    budget = Budget(args.max_steps)
    load_dotenv(ROOT / ".env.local", override=False)
    report = {"completion_metric": COMPLETION_METRIC, "positive_reward_terminal": False,
              "arm": args.arm, "task": args.task, "seed": args.seed,
              "model": MODEL, "max_steps": args.max_steps, "max_recoveries": allowance,
              "controlled_failure_scenario": args.scenario, "failure_injection_confirmed": False,
              "injected_failure_signature": None, "recoveries_used": 0,
              "success": False, "reason": "configuration_error", "steps": 0,
              "reward": 0.0, "terminated": False, "truncated": False,
              "initial_observation_sha256": None}
    env = model = tracked = mapping = None
    started = time.monotonic()
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(budget.run_timeout)
    phase = "setup"
    try:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        html = ROOT / "vendor/miniwob-plusplus/miniwob/html/miniwob"
        if not key or not (html / (args.task + ".html")).is_file():
            raise ValueError("Missing local configuration")
        adapter = OneShotAdapter if args.arm == "oneshot" else ModelAdapter
        model = adapter(key, model=MODEL, max_steps=args.max_steps)
        mapping = (DisabledTextboxOnce() if args.scenario == "disabled_textbox_timeout" else
                   ChangedTextboxIdOnce() if args.scenario == "changed_textbox_id" else action_mapping)
        env = gym.make(f"browsergym/miniwob.{args.task}", headless=True,
                       action_mapping=mapping,
                       task_kwargs={"base_url": html.as_uri() + "/",
                                    "episode_max_time": budget.run_timeout * 1000})
        observation, _ = env.reset(seed=args.seed)
        digest, tree = fingerprint(observation, env)
        report["initial_observation_sha256"] = digest
        tracked = CountedEnv(env)
        phase = "agent"
        if args.arm == "oneshot":
            plan = model.plan(observation["goal"], tree)
            state = execute_plan(tracked, observation, plan, args.max_steps)
        else:
            state = build_workflow(tracked, model, max_steps=args.max_steps,
                                   max_recoveries=allowance).invoke(
                {"observation": observation, "steps": 0},
                {"recursion_limit": 5 * args.max_steps + 2})
        report["recoveries_used"] = state.get("recoveries_used", 0)
        report.update({key: state[key] for key in
                       ("success", "reason", "reward", "terminated", "truncated", "completion_metric", "positive_reward_terminal")})
    except APIStatusError as exc:
        report.update(reason="api_error", http_status=exc.status_code)
    except APIConnectionError:
        report["reason"] = "connection_error"
    except TimeoutError:
        report["reason"] = "timeout"
    except ValueError:
        report["reason"] = "invalid_model_action_or_plan" if phase == "agent" else "configuration_error"
    except RuntimeError:
        report["reason"] = "agent_error" if phase == "agent" else "environment_error"
    except Exception:
        report["reason"] = "environment_error"
    finally:
        try:
            if env is not None:
                env.close()
        except Exception:
            report.update(success=False, reason="cleanup_error")
        try:
            if model is not None:
                model.close()
        except Exception:
            report.update(success=False, reason="cleanup_error")
        signal.alarm(0)
    if ablation and mapping is not None and getattr(mapping, "injected", False) and tracked and tracked.first_failure:
        failure = tracked.first_failure
        report["failure_injection_confirmed"] = failure["action"] == "fill" and failure["fill_timeout"]
        if report["failure_injection_confirmed"]:
            report["injected_failure_signature"] = hashlib.sha256(json.dumps(
                {**failure, "scenario": args.scenario}, sort_keys=True).encode()).hexdigest()
    report.update(steps=tracked.steps if tracked else 0,
                  api_calls=model.calls if model else 0,
                  input_tokens=model.input_tokens if model else 0,
                  output_tokens=model.output_tokens if model else 0,
                  api_usage_may_be_incomplete=report["reason"] in
                  ("api_error", "connection_error", "timeout", "agent_error", "environment_error", "cleanup_error", "invalid_model_action_or_plan"),
                  duration_seconds=round(time.monotonic() - started, 3))
    print(json.dumps(report))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
