# Actual Playwright timeout

This replaced the synthetic exception with a real fill timeout: temporarily disable the
textbox, attempt a fill, then restore the field in a finally block.

```bash
python -m browser_agent --task enter-text --seed 11 --max-steps 3 --max-recoveries 1 --disabled-textbox-timeout-once
```

The intended sequence is timeout → fresh observation → fill → Submit. The failure is
still deliberately induced. A valid result must confirm the timeout and recovery, not
just report eventual success. Click and API failures remain outside this retry policy.

Local plumbing check: `RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_timeout.py -q`.
