# Earlier Wikipedia demo

This was a fixed-site experiment before the form assistant. It types a query, searches
Wikipedia and can open an observed result in a separate browser window.

```bash
python -m app.demo --wikipedia
```

Open `http://127.0.0.1:8765` and try:

> Search Wikipedia for black holes and open the article.

The Python service parses the request, then runs a LangGraph loop over visible search
fields and result links. Actions use fixed code and are checked before execution.
Navigation is restricted to English Wikipedia search and article pages.

The cap is seven model requests. Live runs use API credits; Stop interrupts further work.
A returned article URL doesn't prove the chosen article is the right interpretation of
an ambiguous query. This isn't a research or summarisation tool.

For the current product, see [the Chrome extension](EXTENSION.md).
