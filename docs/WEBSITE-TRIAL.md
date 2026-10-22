# Books to Scrape trial

This was the first external website experiment, separate from MiniWoB and the current
form extension. The task was to open **Travel**, open its first book, and report its title
and price on [Books to Scrape](https://books.toscrape.com/), a demo catalogue.

```bash
python -m website_trial.books --check
python -m website_trial.books
```

`--check` checks dependencies without a model call or browser launch. The second command
uses API credits and opens a fresh browser.

The model chooses only observed link IDs. The adapter checks the destination and verifies
that the final page matches the first book observed in Travel. It allows at most four
calls and link actions, with no basket, login or purchase operations.

One recorded user run completed in two steps and two calls, returning **It's Only the
Himalayas — £45.17**. That's a saved demo result, not a current price or a general website
success rate. Results stay under the ignored `results/` folder.
