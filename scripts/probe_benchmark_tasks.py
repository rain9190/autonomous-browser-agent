"""Development-only local browser observation audit; no model calls or actions."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CONTROL_SELECTOR = "button,input,select,a,[role],.alink,.ui-accordion-header,.ui-tabs-anchor"
# Fixed, read-only DOM metadata extraction. No task ground truth is inspected.
CONTROL_METADATA_JS = """elements => elements.slice(0, 100).map(el => {
  const rect = el.getBoundingClientRect();
  const style = getComputedStyle(el);
  const visible = rect.width > 0 && rect.height > 0 &&
                  style.display !== 'none' && style.visibility !== 'hidden';
  const label = el.labels ? Array.from(el.labels).map(x => x.textContent).join(' ') : '';
  return {bid: el.getAttribute('bid'), tag: el.tagName.toLowerCase(),
    native_id: el.id || null, role_attribute: el.getAttribute('role'),
    input_type: el.getAttribute('type'), aria_label: el.getAttribute('aria-label'),
    aria_expanded: el.getAttribute('aria-expanded'),
    text: (el.textContent || '').trim().slice(0, 160), label: label.trim().slice(0, 160),
    disabled: !!el.disabled, checked: 'checked' in el ? !!el.checked : null,
    visible, link_styled_span: el.tagName === 'SPAN' && el.classList.contains('alink'),
    options: el.tagName === 'SELECT' ? Array.from(el.options).slice(0, 30).map(
      o => ({label: o.label, value: o.value, selected: o.selected})) : []};
})"""


def validate_selection(plan, tasks, seed):
    if seed not in plan["development_seeds"] or seed in plan["reserved_final_seeds"]:
        raise ValueError("Only declared development seeds are allowed")
    allowed = {t["task"] for t in plan["tasks"] if t["selection"] == "provisional_primary"}
    if not tasks or len(tasks) != len(set(tasks)) or any(t not in allowed for t in tasks):
        raise ValueError("Choose distinct primary candidate tasks from the protocol")


def role_map(tree):
    return dict(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\]\s+([A-Za-z][A-Za-z0-9_-]*)", tree))


def make_report(task, seed, observation, tree, controls, count):
    roles = role_map(tree)
    controls = [{**c, "ax_role": roles.get(c.get("bid"))} for c in controls]
    visible = [c for c in controls if c.get("visible")]
    initial = json.dumps({"goal": observation["goal"], "tree": tree}, sort_keys=True)
    return {"task": task, "seed": seed, "status": "observed",
        "evaluation_mode": "development_observation_probe", "api_calls": 0, "actions_executed": 0,
        "goal": observation["goal"], "tree_characters": len(tree),
        "exceeds_current_tree_limit": len(tree) > 8000,
        "tree_truncated_in_record": len(tree) > 16000, "accessibility_tree": tree[:16000],
        "initial_observation_sha256": hashlib.sha256(initial.encode()).hexdigest(),
        "ax_role_counts": dict(Counter(roles.values())),
        "dom_controls_found": count, "dom_controls_truncated": count > 100,
        "controls": controls,
        "visible_generic_link_spans": sum(c.get("link_styled_span", False) and c.get("ax_role") not in ("link", "button") for c in visible),
        "visible_native_selects": sum(c.get("tag") == "select" for c in visible),
        "visible_checkboxes": sum(c.get("input_type") == "checkbox" for c in visible),
        "visible_radios": sum(c.get("input_type") == "radio" for c in visible)}


def observe_task(task, seed):
    import gymnasium as gym
    import browsergym.miniwob  # noqa: F401
    from browsergym.utils.obs import flatten_axtree_to_str
    html = ROOT / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    env = gym.make(f"browsergym/miniwob.{task}", headless=True,
                   task_kwargs={"base_url": html.as_uri() + "/"})
    try:
        observation, _ = env.reset(seed=seed)
        tree = flatten_axtree_to_str(observation["axtree_object"])
        locator = env.unwrapped.page.locator(CONTROL_SELECTOR)
        report = make_report(task, seed, observation, tree,
                             locator.evaluate_all(CONTROL_METADATA_JS), locator.count())
        report["benchmark_data_mode"] = env.unwrapped.page.evaluate(
            "() => typeof WOB_DATA_MODE === 'undefined' ? null : String(WOB_DATA_MODE)")
        return report
    finally:
        env.close()


def run_probe(task, seed):
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
        "--worker", "--tasks", task, "--seed", str(seed)], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=45)
        try:
            record = json.loads(stdout)
            if (isinstance(record, dict) and record.get("task") == task
                    and record.get("seed") == seed and record.get("status") == "probe_error"):
                return {"task": task, "seed": seed, "status": "probe_error", "api_calls": 0,
                        "error_type": record.get("error_type") if re.fullmatch(
                            r"[A-Za-z_][A-Za-z0-9_]{0,80}", str(record.get("error_type", ""))) else "UnknownError"}
            if process.returncode != 0 or record.get("task") != task or record.get("seed") != seed or record.get("status") != "observed":
                raise ValueError()
            return record
        except (ValueError, TypeError, AttributeError):
            return {"task": task, "seed": seed, "status": "probe_error", "api_calls": 0}
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if sys.exc_info()[0] is KeyboardInterrupt:
            raise
        return {"task": task, "seed": seed, "status": "timeout", "api_calls": 0}


def run_audit(plan, tasks, seed, output, runner=run_probe):
    validate_selection(plan, tasks, seed)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    interrupted = False
    try:
        for i, task in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] Inspecting {task}, development seed {seed}", flush=True)
            record = runner(task, seed)
            records.append(record)
            (output / f"{task}-seed{seed}.json").write_text(json.dumps(record, indent=2) + "\n")
            print("  " + record["status"], flush=True)
            if record["status"] != "observed":
                break
    except KeyboardInterrupt:
        interrupted = True
    finally:
        summary = {"evaluation_mode": "development_observation_probe", "seed": seed,
            "planned": len(tasks), "attempted": len(records), "unattempted": len(tasks)-len(records),
            "observed": sum(r["status"] == "observed" for r in records),
            "complete": len(records) == len(tasks) and all(r["status"] == "observed" for r in records),
            "api_calls": 0, "actions_executed": 0, "interrupted": interrupted,
            "tasks_exceeding_current_tree_limit": [r["task"] for r in records if r.get("exceeds_current_tree_limit")],
            "tasks_with_generic_link_spans": [r["task"] for r in records if r.get("visible_generic_link_spans", 0)],
            "task_observations": [{k: r.get(k) for k in ("task", "status", "tree_characters", "ax_role_counts",
                "visible_checkboxes", "visible_radios", "visible_native_selects", "visible_generic_link_spans")} for r in records]}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    plan = json.loads((ROOT / "docs/benchmark/task-plan.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--seed", type=int, default=plan["development_seeds"][0])
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    tasks = args.tasks or [t["task"] for t in plan["tasks"]
                           if t["selection"] == "provisional_primary" and not t["currently_allowlisted"]]
    try:
        validate_selection(plan, tasks, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    if args.worker:
        if len(tasks) != 1:
            parser.error("Worker requires exactly one task")
        try:
            report = observe_task(tasks[0], args.seed)
            print(json.dumps(report))
            return 0
        except Exception as exc:
            print(json.dumps({"task": tasks[0], "seed": args.seed, "status": "probe_error",
                              "error_type": type(exc).__name__, "api_calls": 0}))
            return 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / f"feasibility-{stamp}-{uuid4().hex[:8]}"
    summary = run_audit(plan, tasks, args.seed, output)
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")
    return 0 if summary["complete"] and not summary["interrupted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
