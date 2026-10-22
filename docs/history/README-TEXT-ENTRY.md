# Text entry

This milestone added a fill action alongside clicks. The model reads the requested text
from the MiniWoB instruction, fills an observed textbox, then clicks Submit.

```bash
python -m browser_agent --task enter-text --seed 42
```

A normal successful run takes two actions and two calls. Fill targets must be observed
textboxes; click targets must be allowed buttons. After filling, the agent reads a fresh
observation before deciding again. Completion comes from the benchmark, not just an
error-free fill.
