# Button choices and sequences

After the first click test, the agent gained two tasks: matching a requested button label
and clicking ONE followed by TWO. Each decision uses a fresh observation and bounded
history, rather than hardcoded button IDs.

```bash
python -m browser_agent --task click-button-sequence --seed 42
```

The update had 18 offline tests. It kept the original two-action/two-call allowance.
These are early MiniWoB development tasks, not website automation examples.
