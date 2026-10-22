# Running the demos

The current product is the [Chrome extension](EXTENSION.md). Start there for a form-filling
demo. These commands open the earlier local interfaces at `http://127.0.0.1:8765`:

| Demo | Command |
| --- | --- |
| Separate-browser form assistant | `python -m app.demo` |
| Wikipedia search | `python -m app.demo --wikipedia` |
| MiniWoB results and live benchmark runs | `python -m app.demo --benchmark` |

Run one server at a time. Keep its terminal open and use Ctrl-C to stop it.

The benchmark screen shows saved results without API calls. **Run live** starts a new
paid development run. The text-entry and controlled-timeout examples were user-tested
at seed 61; both finished with full credit.

These earlier demos are separate from the frozen evaluation and from the extension's
current-tab workflow. [Recorded checks](DEMO-VERIFICATION.md)
