import json

import pytest

from browser_agent.evaluate import parse_result, run_suite


def report(success=True):
    return {"task": "click-test", "seed": 7, "success": success,
            "reason": "benchmark_success" if success else "episode_ended_without_success",
            "terminated": True, "truncated": False,
            "reward": 1.0 if success else 0.0,
            "steps": 1, "api_calls": 1, "input_tokens": 100, "output_tokens": 10}


def test_parse_success():
    result = parse_result(json.dumps(report()), 0, "click-test", 7)
    assert result["success"] and result["api_calls"] == 1


@pytest.mark.parametrize("change", [{"seed": 123}, {"reward": 0},
    {"truncated": True}, {"api_calls": 3}, {"success": "true"}])
def test_reject_invalid_or_mismatched_report(change):
    data = {**report(), **change}
    assert parse_result(json.dumps(data), 0, "click-test", 7)["status"] == "invalid_report"


def test_benchmark_failure_is_valid_data():
    result = parse_result(json.dumps(report(False)), 1, "click-test", 7)
    assert result["status"] == "benchmark_failure"


def test_failure_text_is_not_saved():
    result = parse_result("API request failed (HTTP 429); SECRET", 1, "click-test", 7)
    assert result["status"] == "api_quota_or_rate_limit"
    assert "SECRET" not in json.dumps(result)


def fake(task, seed, status="success"):
    return {"task": task, "seed": seed, "status": status,
            "success": status == "success", "api_calls": 1,
            "input_tokens": 100, "output_tokens": 10}


def test_six_episodes_saved_and_summarized(tmp_path):
    output = tmp_path / "evaluation"
    result = run_suite(["click-test", "click-button", "click-button-sequence"],
                       [7, 123], output, runner=fake)
    assert result["complete"] and result["successes"] == 6
    assert result["api_call_ceiling"] == 12
    assert result["reported_input_tokens"] == 600
    assert len(list(output.glob("*.json"))) == 7
    assert json.loads((output / "summary.json").read_text()) == result


def test_stop_after_infrastructure_error(tmp_path):
    def runner(task, seed):
        return {**fake(task, seed, "api_error"), "api_calls": None,
                "input_tokens": None, "output_tokens": None}
    result = run_suite(["click-test"], [7, 123], tmp_path / "eval", runner)
    assert result["attempted"] == 1 and result["unattempted"] == 1
    assert result["episodes_with_unknown_api_usage"] == 1
    assert not result["complete"]


def test_benchmark_failure_does_not_stop_suite(tmp_path):
    result = run_suite(["click-test"], [7, 123], tmp_path / "eval",
                       lambda t, s: fake(t, s, "benchmark_failure"))
    assert result["complete"] and result["success_rate_on_attempted"] == 0


@pytest.mark.parametrize("tasks,seeds", [(["click-test"], list(range(13))),
    (["click-test"], [7, 7]), (["unknown"], [7])])
def test_invalid_suite_starts_no_episodes(tmp_path, tasks, seeds):
    def forbidden(*_):
        raise AssertionError("Must not start")
    with pytest.raises(ValueError):
        run_suite(tasks, seeds, tmp_path / "eval", forbidden)
    assert not (tmp_path / "eval").exists()


def test_interruption_preserves_partial_summary(tmp_path):
    def interrupt(*_):
        raise KeyboardInterrupt()
    result = run_suite(["click-test"], [7], tmp_path / "eval", interrupt)
    assert result["interrupted"] and result["attempted"] == 0
    assert (tmp_path / "eval/summary.json").exists()


def test_episode_timeout_kills_process_group(monkeypatch):
    import subprocess
    from browser_agent.evaluate import run_episode
    class Process:
        pid = 98765
        calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("test", timeout)
            return "", "private stderr"
    killed = []
    monkeypatch.setattr("browser_agent.evaluate.subprocess.Popen", lambda *a, **k: Process())
    monkeypatch.setattr("browser_agent.evaluate.os.killpg", lambda *args: killed.append(args))
    result = run_episode("click-test", 7)
    assert result["status"] == "timeout" and result["api_calls"] is None
    assert killed[0][0] == 98765


def test_episode_uses_current_stdout_and_no_shell(monkeypatch):
    from browser_agent.evaluate import run_episode
    class Process:
        returncode = 0
        def communicate(self, timeout=None):
            return json.dumps(report()), "private stderr"
    def spawn(command, **kwargs):
        assert command[-4:] == ["--task", "click-test", "--seed", "7"]
        assert "shell" not in kwargs and kwargs["start_new_session"]
        return Process()
    monkeypatch.setattr("browser_agent.evaluate.subprocess.Popen", spawn)
    assert run_episode("click-test", 7)["success"]
