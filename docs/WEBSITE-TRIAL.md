# First externally hosted website trial

Separate experiment `books_to_scrape_trial_v1`. The frozen MiniWoB source, protocol and
132 final episode records are unchanged. This trial uses an iterative model-driven
link-selection loop and a new fixed-site adapter; it does not reuse MiniWoB reward flags
or establish a general-purpose website agent.

## Fixed task and scope

Start at https://books.toscrape.com/ and ask: **Open the Travel category, open its first
listed book, and report the title and price.** The public site identifies itself as a
scraping demo with artificial prices/ratings, not a real shop. Sources inspected during
preparation: the home page and its Travel catalogue at
https://books.toscrape.com/catalogue/category/books/travel_2/index.html .

The adapter does not hardcode a book title, price, category destination URL or action
sequence. Each observation lists visible labelled anchors and their URLs, preserving DOM
order and identifying book-title links. The model selects the next observed link ID.
IDs expire after navigation. The executor rechecks the anchor's identity and visibility
before a native click; arbitrary model code and model-provided URLs are not accepted.
Only a fixed title/price extractor and verification rule decide completion.

Success requires visiting a page headed Travel, remembering its first observed book-title
URL, reaching that exact URL, and finding a title, GBP-format price and Travel breadcrumb
on the detail page. A wrong book or a direct product visit without Travel observation
cannot pass. This is goal-specific DOM verification, not an independent benchmark reward.

## Controls and limits

- At most four model calls and four link actions; no automatic retries or recovery.
- Same existing model snapshot, request timeout 20 seconds, max_retries=0, store=False,
  at most 128 output tokens per action. Input and catalogue lengths are bounded.
- A 130-second process alarm, plus per-operation browser timeouts. macOS/POSIX assumed.
- Fresh nonpersistent Chromium context; no existing browser profile or saved credentials.
- HTTPS books.toscrape.com only; catalogue HTML navigation only. Fixed host is not configurable.
  Requests to other origins and all non-GET/HEAD requests are blocked; service workers are
  blocked. Downloads are not accepted and popups are closed. This is a constrained demo,
  not a comprehensive hostile-website security sandbox or a total network-byte cap.
- No basket, form, login, purchasing, arbitrary JavaScript, shell or file-upload actions.
- Page content is treated as untrusted model input. No plaintext API key or exception body
  is logged. The existing ignored .env.local is loaded only for an explicit live run.
- New result JSON includes action observations and outcomes under ignored `results/`.
  Interrupted/failed requests retain usage uncertainty. Reports never overwrite an earlier run.

## Run on the existing Mac environment

No extra dependencies are needed beyond the installed Playwright/OpenAI/Pydantic/dotenv.
Install the update, run offline tests and verify the old freeze first:

```bash
python -m pytest tests -q
python scripts/check_benchmark_plan.py
python -m website_trial.books --check
```

All three commands above use zero model requests and launch no browser. `--check` only
checks package availability, not internet connectivity, browser installation or API access.

Then start one live trial:

```bash
python -m website_trial.books
```

This opens a visible fresh Chromium window and can make at most four paid requests using
the existing approved local key. Do not interact with the automation's browser while it
runs. The agent should choose Travel, then its first book; actual choices are not guaranteed.
Each observe/validate/execute event is printed. At completion, share the final JSON and
results path, including failures. Ctrl-C stops the run and attempts resource cleanup.

If a display is unavailable, `--headless` hides the browser. SSL/network failures stop the
trial; TLS verification is not disabled. Site layout or content changes may invalidate this
fixed verifier. Initial success or failure has not been established by the offline tests;
only user-run live evidence can establish it. Do not add its result to final MiniWoB rates.
