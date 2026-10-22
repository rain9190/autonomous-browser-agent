# Chrome extension

The panel fills supported fields in your current tab. It needs the local Python service
running in the background.

## Setup

Complete the [README setup](../README.md#get-started), then run:

```bash
source .venv/bin/activate
python -m extension_service.server
```

1. Open `chrome://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select this project's `extension/` folder.
3. Open a form and click the extension icon.
4. In **Settings**, enter the connection code from the terminal.

The code changes when the service restarts. It isn't your API key.
After an extension update, click **Reload** in Chrome and refresh the website tab.

## First try

Open the [practice form](http://127.0.0.1:8766/practice) and enter:

```text
Name: Alex Example
Email: alex@example.com
Organization: Example University
Session: Afternoon
Attend Day 1 and Day 2. Dietary preference: Vegetarian.
```

Click **Fill form**. It should fill both sections and stop for review. Practice submission
is disabled. Missing details and conflicting existing answers trigger a question.

## What works

Text/search inputs, text areas, native choices and dropdowns, Google Forms controls,
and simple editable regions. Detection includes fields outside forms, open shadow roots
and accessible same-origin frames.

Be specific: “Type Paris in the search box and leave everything else blank.” Keep the
form tab active. Uploads, CAPTCHA, passwords, closed shadow roots, cross-origin frames
and some custom controls need manual input. Only supported in-page Next steps are automated.

## Things to know

- Relevant fields and instructions go to OpenAI; live runs use API credits.
- The key stays in Python. The app doesn't save answer profiles or logs.
- Stop doesn't undo earlier entries or recall an in-flight API request.
- The agent never clicks Submit, but websites may autosave while you type.
- Each run is limited to 24 model calls, 60 interactions and ten minutes.

Seven local browser checks use simulated responses. They don't prove every website works.
