"""Read-only source/registration check. Does not launch a browser or call an API."""
import hashlib
import json
from pathlib import Path

import gymnasium as gym
import browsergym.miniwob  # noqa: F401


def main():
    root = Path(__file__).resolve().parents[1]
    plan = json.loads((root / "docs/benchmark/task-plan.json").read_text())
    primary = [t for t in plan["tasks"] if t["selection"] == "provisional_primary"]
    assert len(primary) == plan["primary_task_count"] == 20
    assert len({t["task"] for t in plan["tasks"]}) == len(plan["tasks"])
    assert not set(plan["development_seeds"]) & set(plan["reserved_final_seeds"])
    assert not set(plan["previously_used_seeds"]) & set(plan["reserved_final_seeds"])
    html = root / "vendor/miniwob-plusplus/miniwob/html/miniwob"
    for task in plan["tasks"]:
        path = html / (task["task"] + ".html")
        assert path.is_file(), f"Missing task HTML: {task['task']}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == task["task_html_sha256"], f"Task source changed: {task['task']}"
        gym.spec("browsergym/miniwob." + task["task"])
    calls = sum(t["action_budget"] + 1 for t in primary) * len(plan["reserved_final_seeds"])
    assert calls == plan["baseline_reserved_final_call_ceiling"]
    print(json.dumps({"source_and_registration_check": "passed",
        "primary_candidates": len(primary), "implemented_tasks": plan["implemented_task_count"],
        "new_candidates": len(primary) - plan["implemented_task_count"],
        "reserve_tasks": len(plan["tasks"]) - len(primary),
        "protocol_status": plan["status"], "api_calls_made": 0,
        "browsers_launched": 0}, indent=2))


if __name__ == "__main__":
    main()
