# Using the Chrome extension

The extension fills fields in the tab you have open. A local Python service handles the
model requests; the side panel only needs your instructions, Fill form and Stop.

## Setup

Follow the [README setup](../README.md#try-it) first, then start the service:

```bash
source .venv/bin/activate
python -m extension_service.server
```

Keep the terminal open.

1. Open `chrome://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select this project's `extension/` folder.
3. Open your form and click the extension icon.
4. In **Settings**, paste the connection code printed in the terminal and click **Connect**.

The connection code is not your API key. It changes when you restart the service.
After updating the extension, click **Reload** in Chrome and refresh the website tab.

## Try it

Open the [practice form](http://127.0.0.1:8766/practice) while the service is running.
Enter these details in the panel:

```text
Name: Alex Example
Email: alex@example.com
Organization: Example University
Session: Afternoon
Attend Day 1 and Day 2. Dietary preference: Vegetarian.
```

Click **Fill form** and watch the two sections fill. Practice submission is disabled.
The agent asks for missing required details and permission to replace existing answers.
**Stop** halts further actions but doesn't undo what was already entered.

## Supported fields

Text inputs, search boxes, text areas, native dropdowns, radio buttons, checkboxes and
simple editable text regions. It also checks fields outside forms, open shadow roots
and accessible same-origin frames. Google Forms has a separate question adapter.

Be specific, for example: “Type Paris in the search box and leave everything else blank.”
Every detected textbox is a candidate; unrelated boxes are not filled automatically.

File uploads, CAPTCHA, passwords, sensitive declarations, closed shadow roots,
cross-origin frames and some custom widgets still need manual input. Only supported
in-page Next transitions are automated. Keep the form tab active and review before submitting.

## Data and limits

Relevant form fields, current answers and your instructions go to OpenAI. Live runs use
API credits. The key stays in Python, and the app doesn't save answer profiles or logs.
Websites may autosave as you type, even though the agent never clicks Submit.

Each run allows up to 24 model calls, 60 counted interactions, 40 questions, eight sections
and ten minutes. These aren't monetary billing caps; an in-flight API call may still be
billed after Stop.

Seven automated browser checks cover local fixtures with simulated model responses.
They don't establish compatibility with every website.
