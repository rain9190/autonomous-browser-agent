# Earlier separate-browser form app

This version opens a fresh Chromium window. For the current-tab product, use the
[Chrome extension](EXTENSION.md).

```bash
python -m app.demo
```

Open `http://127.0.0.1:8765`, select **Try a practice form**, then **Fill form**.
For a real run, supply a public Google Forms responder link and your details.
Live runs use the key in `.env.local` and API credits.

The app supports ordinary text and choice questions plus supported Next sections.
It asks for missing required answers, checks entered values and stops before Submit.
Protected or unsupported questions are listed for manual review. Stop closes the task,
but doesn't undo answers already entered; Google Forms may autosave them.

The shared planner uses the same observe → decide → validate → execute → verify loop
as the extension. Four local browser checks used simulated plans; the supplied Google
Form was also inspected read-only during this version's preparation.
