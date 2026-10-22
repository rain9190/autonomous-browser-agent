# Longer tasks and progress

The synthetic MiniWoB login task needed three actions: enter two generated values and
click Login. That led to configurable action/call budgets and per-attempt progress records.

```bash
python -m browser_agent --task login-user --seed 42 --max-steps 3
```

Progress separates execution from benchmark success. Failed attempts still consume budget,
and reported field execution alone doesn't prove the task is correct. The update had
59 offline tests. This is a generated benchmark login, not a real account login.
