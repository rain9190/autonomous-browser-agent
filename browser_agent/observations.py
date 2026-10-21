"""Read-only metadata for visible benchmark-specific link spans."""
import re

LINK_TASKS = {"browsergym/miniwob.click-link", "browsergym/miniwob.click-collapsible-2",
              "browsergym/miniwob.click-tab-2-easy", "browsergym/miniwob.click-tab-2-medium"}
LINK_PREDICATE_JS = r"""(el) => {
  const r = el.getBoundingClientRect(), s = getComputedStyle(el);
  return location.protocol === 'file:' &&
    /\/(click-link|click-collapsible-2|click-tab-2-easy|click-tab-2-medium)\.html$/.test(location.pathname) &&
    el.matches('#area span.alink') && r.width > 0 && r.height > 0 &&
    s.display !== 'none' && s.visibility === 'visible' &&
    !el.closest('[hidden],[aria-hidden="true"]');
}"""
LINK_READ_JS = """elements => elements.filter(""" + LINK_PREDICATE_JS + """).map(el =>
  ({bid: el.getAttribute('bid'), label: el.textContent.trim()}))"""


def link_environment(env):
    for _ in range(8):
        if getattr(getattr(env, "spec", None), "id", None) in LINK_TASKS:
            return env
        next_env = getattr(env, "env", None)
        if next_env is None or next_env is env:
            break
        env = next_env
    return None


def format_links(records):
    if not isinstance(records, list) or len(records) > 40:
        raise ValueError("Benchmark link metadata exceeds bounds")
    validated = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid benchmark link metadata")
        bid, label = record.get("bid"), record.get("label")
        if (not isinstance(bid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", bid)
                or not isinstance(label, str) or not 0 < len(label) <= 256 or bid in seen):
            raise ValueError("Invalid benchmark link metadata")
        seen.add(bid)
        validated.append((bid, label))
    return "\n".join(f"[{bid}] benchmark_link {label!r}" for bid, label in sorted(validated))


def enrich_benchmark_links(env, tree):
    local = link_environment(env)
    if local is None:
        return tree
    records = local.unwrapped.page.locator("#area span.alink").evaluate_all(LINK_READ_JS)
    supplement = format_links(records)
    return tree + ("\n" + supplement if supplement else "")
