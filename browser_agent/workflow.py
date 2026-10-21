from typing import Any, TypedDict

from browsergym.utils.obs import flatten_axtree_to_str
from langgraph.graph import END, START, StateGraph

from .budget import Budget
from .observations import enrich_benchmark_links
from .metrics import COMPLETION_METRIC, full_credit_success, positive_reward_terminal
from .actions import button_ids, textbox_ids, tab_ids, benchmark_link_ids, selection_targets, validate_action


class State(TypedDict, total=False):
    observation: dict
    tree: str
    allowed: set[str]
    editable: set[str]
    selection: dict
    tabs: set[str]
    benchmark_links: set[str]
    proposal: Any
    payload: str
    steps: int
    reward: float
    terminated: bool
    truncated: bool
    success: bool
    reason: str
    history: list[dict]
    progress: list[dict]
    remaining_steps: int
    completion_metric: str
    positive_reward_terminal: bool
    trace: list[str]
    last_attempt: dict
    failed_actions: list[dict]
    recovery_context: dict | None
    recoveries_used: int


def build_workflow(env, model, max_steps=2, max_recoveries=0):
    budget = Budget(max_steps)
    if type(max_recoveries) is not int or not 0 <= max_recoveries <= 2:
        raise ValueError("Recovery budget must be an integer from 0 to 2")
    def observe(s):
        tree = enrich_benchmark_links(env, flatten_axtree_to_str(s["observation"]["axtree_object"]))
        if len(tree) > 8000:
            raise ValueError("Accessibility tree exceeds input budget")
        allowed = button_ids(tree)
        editable = textbox_ids(tree)
        selection = selection_targets(tree)
        tabs = tab_ids(tree)
        links = benchmark_link_ids(tree)
        if not allowed and not editable and not any(selection.values()) and not tabs and not links:
            raise ValueError("No supported elements in the observation")
        return {"tree": tree, "allowed": allowed, "editable": editable, "selection": selection, "tabs": tabs, "benchmark_links": links,
                "trace": s.get("trace", []) + ["observe"]}

    def decide(s):
        if s.get("steps", 0) >= budget.max_steps:
            raise RuntimeError("Step budget exhausted")
        args = (s["observation"]["goal"], s["tree"], s.get("history", []))
        proposal = (model.decide(*args, recovery_context=s["recovery_context"])
                    if s.get("recovery_context") else model.decide(*args))
        return {"proposal": proposal,
                "trace": s["trace"] + ["decide"]}

    def validate(s):
        action = validate_action(s["proposal"], s["allowed"], s["editable"], s["selection"], s["tabs"], s["benchmark_links"])
        return {"payload": action.model_dump_json(exclude_none=True),
                "trace": s["trace"] + ["validate"]}

    def execute(s):
        action = validate_action(s["proposal"], s["allowed"], s["editable"], s["selection"], s["tabs"], s["benchmark_links"])
        observation, reward, terminated, truncated, _ = env.step(s["payload"])
        attempted = action.model_dump(exclude_none=True)
        error = bool(observation.get("last_action_error"))
        history = s.get("history", []) + ([] if error else [attempted])
        failed = s.get("failed_actions", []) + ([{"action": action.action, "bid": action.bid}] if error else [])
        return {"observation": observation, "history": history, "failed_actions": failed,
                "last_attempt": attempted, "reward": float(reward),
                "terminated": bool(terminated), "truncated": bool(truncated),
                "steps": s.get("steps", 0) + 1,
                "trace": s["trace"] + ["execute"]}

    def verify(s):
        error = bool(s["observation"].get("last_action_error"))
        diagnostic = str(s["observation"].get("last_action_error", ""))
        # Store only a category, never the locator diagnostic or page content.
        error_kind = ("playwright_fill_timeout" if error
                      and diagnostic.startswith("TimeoutError:")
                      and "Locator.fill" in diagnostic
                      and "exceeded" in diagnostic else
                      "browser_action_error" if error else None)
        positive = positive_reward_terminal(s["reward"], s["terminated"], s["truncated"], error)
        success = full_credit_success(s["reward"], s["terminated"], s["truncated"], error)
        if success:
            reason = "benchmark_success"
        elif error:
            # Fill replaces a value and can be retried after a fresh observation.
            # Clicks can have effects despite reporting an error; stop on those.
            if (s["last_attempt"]["action"] == "fill"
                    and not s["terminated"] and not s["truncated"]
                    and s["steps"] < budget.max_steps
                    and s.get("recoveries_used", 0) < max_recoveries):
                reason = "recover"
            else:
                reason = "browser_action_error"
        elif positive and s["reward"] < 1:
            reason = "partial_credit_terminal"
        elif s["terminated"] or s["truncated"]:
            reason = "episode_ended_without_success"
        elif s["steps"] >= budget.max_steps:
            reason = "step_budget_exhausted"
        else:
            reason = "continue"
        action = s["last_attempt"]
        progress = s.get("progress", []) + [{
            "step": s["steps"], "action": action["action"], "bid": action["bid"],
            "execution_ok": not error, "benchmark_success": success,
            "error_kind": error_kind,
            "failed_fill_target_absent": bool(error and action["action"] == "fill"
                and action["bid"] not in textbox_ids(flatten_axtree_to_str(
                    s["observation"]["axtree_object"]))),
        }]
        recovery_context = ({"action": action["action"], "bid": action["bid"],
                             "status": "previous_fill_failed"} if reason == "recover" else None)
        return {"success": success, "reason": reason, "progress": progress,
                "completion_metric": COMPLETION_METRIC, "positive_reward_terminal": positive,
                "recovery_context": recovery_context,
                "recoveries_used": s.get("recoveries_used", 0) + int(reason == "recover"),
                "remaining_steps": budget.max_steps - s["steps"],
                "trace": s["trace"] + ["verify"]}

    graph = StateGraph(State)
    for name, node in [("observe", observe), ("decide", decide),
                       ("validate", validate), ("execute", execute), ("verify", verify)]:
        graph.add_node(name, node)
    graph.add_edge(START, "observe")
    for a, b in zip(["observe", "decide", "validate", "execute"],
                    ["decide", "validate", "execute", "verify"]):
        graph.add_edge(a, b)
    graph.add_conditional_edges("verify", lambda s: "observe" if s["reason"] in ("continue", "recover") else END)
    return graph.compile()
