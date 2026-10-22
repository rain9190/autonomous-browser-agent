# Autonomous Browser Agent

A Chrome extension that fills forms from plain-English instructions.

Open a form, tell it what to enter, and watch the fields fill in your current tab.
It asks for missing details and leaves submission to you.

**Python · LangGraph · OpenAI API · Pydantic · JavaScript**

## Get started

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
```

Skip this setup if you already have the environment and key file.
Add your OpenAI API key to `.env.local`, then run:

```bash
python -m extension_service.server
```

In Chrome, open `chrome://extensions`, enable **Developer mode**, and **Load unpacked**
from the `extension/` folder. Open a form, click the extension icon, and enter the
terminal's connection code in **Settings**.

Keep the terminal running. Start with the [practice form](http://127.0.0.1:8766/practice).
[Full setup](docs/EXTENSION.md)

## What it does

- Fills text fields, dropdowns, radio buttons and checkboxes.
- Finds standalone textboxes and simple editable regions too.
- Asks before replacing existing answers and checks what it entered.
- Handles supported sections, with a Stop button when needed.

Uploads, CAPTCHA, passwords and some custom controls still need manual input.
Relevant form data goes to OpenAI; the key stays in the local Python service.

## How it works

**Observe → decide → validate → execute → verify**

LangGraph runs the loop. Pydantic checks the model's proposed actions, and a fixed DOM
adapter carries them out. The agent doesn't execute model-generated JavaScript.

## Results

The project started with local BrowserGym/MiniWoB tasks before becoming an extension.
Across 20 tasks and three seeds each, one-shot planning passed **55/60** and iterative
planning passed **57/60**. These aren't real-website success rates.

There are also **340 regression tests** and **seven targeted browser checks** using
simulated model responses.

```bash
python -m pytest tests -q
RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser_extension.py -q
```

[Benchmark report](docs/FINAL-BENCHMARK-REPORT.md) · [Project notes](docs/PROJECT-DETAILS.md)
