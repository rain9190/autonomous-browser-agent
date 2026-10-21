import json

import pytest

from scripts import probe_benchmark_tasks as probe


@pytest.fixture
def plan():
    return {"development_seeds": [61, 67], "reserved_final_seeds": [1009, 1013, 1019],
            "tasks": [{"task": "click-link", "selection": "provisional_primary"},
                      {"task": "choose-list", "selection": "provisional_primary"},
                      {"task": "reserve", "selection": "reserve_blocked"}]}


@pytest.mark.parametrize("seed", [1009, 1013, 1019, 11])
def test_non_development_seeds_rejected(plan, seed):
    with pytest.raises(ValueError):
        probe.validate_selection(plan, ["click-link"], seed)


@pytest.mark.parametrize("tasks", [[], ["reserve"], ["unknown"], ["click-link", "click-link"]])
def test_bad_task_selection_rejected(plan, tasks):
    with pytest.raises(ValueError):
        probe.validate_selection(plan, tasks, 61)


def test_read_only_report_correlates_dom_and_ax_roles():
    controls = [{"bid": "1", "tag": "span", "link_styled_span": True, "visible": True},
                {"bid": "2", "tag": "select", "visible": True},
                {"bid": "3", "tag": "input", "input_type": "checkbox", "visible": True},
                {"bid": "4", "tag": "input", "input_type": "radio", "visible": False}]
    result = probe.make_report("click-link", 61, {"goal": "Click requested link"},
        "[1] generic 'Link'\n[2] combobox\n[3] checkbox\n[4] radio", controls, 4)
    assert result["visible_generic_link_spans"] == 1
    assert result["visible_native_selects"] == result["visible_checkboxes"] == 1
    assert result["visible_radios"] == 0 and result["api_calls"] == result["actions_executed"] == 0
    assert result["controls"][0]["ax_role"] == "generic"
    assert len(result["initial_observation_sha256"]) == 64


def test_large_observation_is_flagged_not_silently_accepted():
    result = probe.make_report("task", 61, {"goal": "goal"}, "x" * 17000, [], 101)
    assert result["exceeds_current_tree_limit"] and result["tree_truncated_in_record"]
    assert result["dom_controls_truncated"] and len(result["accessibility_tree"]) == 16000


def observed(task, seed):
    return {"task": task, "seed": seed, "status": "observed", "api_calls": 0,
            "tree_characters": 100, "ax_role_counts": {"button": 1}}


def test_audit_writes_all_records_and_summary(plan, tmp_path):
    summary = probe.run_audit(plan, ["click-link", "choose-list"], 61, tmp_path / "audit", observed)
    assert summary["complete"] and summary["observed"] == 2
    assert len(list((tmp_path / "audit").glob("*.json"))) == 3
    assert json.loads((tmp_path / "audit/summary.json").read_text()) == summary


def test_failed_probe_stops_without_discarding_result(plan, tmp_path):
    summary = probe.run_audit(plan, ["click-link", "choose-list"], 61, tmp_path / "audit",
        lambda t, s: {"task": t, "seed": s, "status": "probe_error"})
    assert not summary["complete"] and summary["attempted"] == summary["unattempted"] == 1


def test_reserved_seed_rejected_before_browser_worker(plan, tmp_path):
    with pytest.raises(ValueError):
        probe.run_audit(plan, ["click-link"], 1009, tmp_path / "audit",
                        lambda *_: pytest.fail("Must not run"))
    assert not (tmp_path / "audit").exists()


def test_interrupt_preserves_partial_summary(plan, tmp_path):
    def interrupt(*_):
        raise KeyboardInterrupt()
    summary = probe.run_audit(plan, ["click-link"], 61, tmp_path / "audit", interrupt)
    assert summary["interrupted"] and summary["unattempted"] == 1
    assert (tmp_path / "audit/summary.json").exists()


def test_subprocess_timeout_cleans_browser_group(monkeypatch):
    import subprocess
    class Process:
        pid = 98765
        calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("test", timeout)
            return "", ""
    killed = []
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(probe.os, "killpg", lambda *a: killed.append(a))
    assert probe.run_probe("click-link", 61)["status"] == "timeout"
    assert killed[0][0] == 98765
