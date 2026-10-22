# Full-credit scoring

Some checkbox tasks award partial positive reward even when an answer is wrong. The
project therefore counts success only when reward is 1.0, the episode terminated, and
there was no truncation or final action error.

The shared metric is `terminal_full_credit_reward_1_v1`. Both planners and the evaluation
parsers use it; raw reward is still retained. This prevents partial credit from appearing
as a completed task.

```bash
python -m pytest tests/test_full_credit.py -q
```

Older evidence wasn't rewritten when the metric was added.
