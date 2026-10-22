# Demo checks

## Earlier benchmark interface — 22 October 2026

User screenshots and terminal output showed these seed-61 runs:

| Run | Result | Calls | Action attempts | Recoveries |
| --- | --- | ---: | ---: | ---: |
| Text entry | Full credit, exit 0 | 2 | 2 | 0 |
| Controlled fill timeout | Full credit, exit 0 | 3 | 3 | 1 |

The saved overview also displayed 55/60 one-shot, 57/60 iterative and 6/6 recovery-on.
These development runs are separate from the 132 final benchmark episodes.
Demo commit: `332f646`; report commit: `aba1584`.

## Chrome extension

A later user screenshot showed a real Google Form with the supplied name and roll number
filled and **No** selected for the registration question. The assistant reported
**Needs your review** for the screenshot upload and left Submit untouched.

That demonstrates this form path. It doesn't establish a success rate across websites,
active cancellation or clean-machine installation.
