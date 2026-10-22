# Autonomous Browser Agent

A Chrome extension that fills forms from plain-English instructions.

Open a form, tell the agent what to enter, and watch it fill the fields in your current tab.
It asks when something is missing and leaves the final submission to you.

**Python · LangGraph · OpenAI API · Pydantic · JavaScript · Chrome Extensions**

## What it can do

- Fill text fields, dropdowns, radio buttons and checkboxes.
- Find textboxes outside standard forms, including search boxes and simple editable regions.
- Ask before replacing an existing answer.
- Check what it entered, move through supported sections, and stop when you ask.

It works with Google Forms and ordinary web inputs. File uploads, CAPTCHA, protected fields
and some custom controls still need manual input.

## Try it

From the project folder, set up the Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
```

If you already have `.venv` and `.env.local`, keep them and skip the setup above.
Add your OpenAI API key to `.env.local`, then start the service:

```bash
python -m extension_service.server
```

1. Open `chrome://extensions`, enable **Developer mode**, and click **Load unpacked**.
2. Select the `extension/` folder from this project.
3. Open a form and click the extension icon.
4. Paste the terminal's connection code into **Settings**, enter your instructions, and click **Fill form**.

Keep the terminal running. To try it first, open the [practice form](http://127.0.0.1:8766/practice).
Relevant form data goes to OpenAI, and live runs use API credits. The key stays in the local service.

## How it works

**Observe → decide → validate → execute → verify**

The extension reads the page's fields. A Python service uses LangGraph and structured model
responses to decide what to fill. It checks each action before executing it, then reads the
field back to verify the result. It doesn't execute model-generated JavaScript.

## Testing

This project started with BrowserGym/MiniWoB before becoming a browser extension.
Across 20 tasks and three seeds per task:

| Approach | Successful runs |
| --- | --- |
| One-shot planning | 55/60 |
| Iterative planning | 57/60 |

These are local benchmark results, not success rates on real websites. The project also has
340 regression tests and seven targeted browser checks using simulated model responses.

```bash
python -m pytest tests -q
RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_extension.py -q
```

[Setup and supported forms](docs/EXTENSION.md) · [Benchmark report](docs/FINAL-BENCHMARK-REPORT.md)
