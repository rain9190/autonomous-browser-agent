import re
import ast
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .observations import LINK_PREDICATE_JS


class ClickAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["click"]
    bid: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["click", "fill", "set_checked", "check_radio", "select_option", "activate_tab", "click_benchmark_link"]
    bid: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    text: str | None = Field(default=None, max_length=256)
    checked: bool | None = None

    @model_validator(mode="after")
    def check_text(self):
        if self.action in ("fill", "select_option"):
            if self.text is None or self.text == "":
                raise ValueError("Fill/select require nonempty text")
        elif self.text is not None:
            raise ValueError("This action must have null text")
        if self.action == "set_checked":
            if self.checked is None:
                raise ValueError("Set_checked requires a boolean checked value")
        elif self.checked is not None:
            raise ValueError("Only set_checked may supply checked")
        return self


class ObservedRoleMismatch(ValueError):
    def __init__(self, action, bid, roles):
        super().__init__("The selected ID does not match the observed action role")
        self.requested_action = action
        self.target_bid = bid
        self.observed_roles = roles


def button_ids(tree: str) -> set[str]:
    # IDs and roles come from BrowserGym's accessibility tree, not model claims.
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] button\b", tree))


def textbox_ids(tree: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] textbox\b", tree))


def tab_ids(tree: str) -> set[str]:
    # Require an observed controlled panel. The benchmark can assign a spurious
    # tab role to a Submit wrapper that has no panel; exclude that wrapper.
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] tab\b[^\n]*\bcontrols=", tree))


def benchmark_link_ids(tree: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] benchmark_link\b", tree))


def selection_targets(tree: str) -> dict:
    """Read observed AX roles and option labels under each combobox."""
    result = {"checkbox": set(), "radio": set(), "select_options": {}}
    current = None
    parent_indent = -1
    pattern = re.compile(r"^\s*\[([A-Za-z0-9_-]{1,64})\]\s+(\w+)\b(.*)$")
    literal = re.compile(r'''^\s*('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")''')
    for line in tree.expandtabs(4).splitlines():
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent <= parent_indent:
            current = None
        match = pattern.match(line)
        if not match:
            continue
        bid, role, rest = match.groups()
        if role in ("checkbox", "radio"):
            result[role].add(bid)
        if role == "combobox":
            current, parent_indent = bid, indent
            result["select_options"][bid] = []
        elif role == "option" and current is not None:
            label_match = literal.match(rest)
            if label_match:
                try:
                    # Literal string parsing only; never eval executable text.
                    label = ast.literal_eval(label_match.group(1))
                except (SyntaxError, ValueError):
                    continue
                if isinstance(label, str) and 0 < len(label) <= 256:
                    result["select_options"][current].append(label)
    return result


def action_catalog(tree: str) -> dict:
    """Legal targets only; contains no solution or task-specific target choice."""
    selection = selection_targets(tree)
    options = {bid: [label for label in labels if labels.count(label) == 1]
               for bid, labels in selection["select_options"].items()}
    return {"click": sorted(button_ids(tree)), "fill": sorted(textbox_ids(tree)),
            "activate_tab": sorted(tab_ids(tree)),
            "click_benchmark_link": sorted(benchmark_link_ids(tree)),
            "set_checked": sorted(selection["checkbox"]),
            "check_radio": sorted(selection["radio"]),
            "select_option": {bid: labels for bid, labels in options.items() if labels}}


def validate_action(raw: object, allowed: set[str], editable: set[str] | None = None,
                    selection: dict | None = None, tabs: set[str] | None = None,
                    benchmark_links: set[str] | None = None) -> Action:
    action = Action.model_validate(raw)
    selection = selection or {"checkbox": set(), "radio": set(), "select_options": {}}
    targets = {"click": allowed, "fill": editable or set(),
               "set_checked": selection["checkbox"], "check_radio": selection["radio"],
               "select_option": set(selection["select_options"]), "activate_tab": tabs or set(),
               "click_benchmark_link": benchmark_links or set()}[action.action]
    if action.bid not in targets:
        roles = {"button": allowed, "textbox": editable or set(),
                 "checkbox": selection["checkbox"], "radio": selection["radio"],
                 "combobox": set(selection["select_options"]), "tab": tabs or set(),
                 "benchmark_link": benchmark_links or set()}
        raise ObservedRoleMismatch(action.action, action.bid,
                                   [role for role, ids in roles.items() if action.bid in ids])
    if action.action == "select_option" and selection["select_options"][action.bid].count(action.text) != 1:
        raise ValueError("Select requires one unambiguous observed option label")
    return action


def action_mapping(payload: str) -> str:
    # BrowserGym requires Python internally. Generate only this fixed template
    # from validated JSON; never forward model-generated Python to BrowserGym.
    action = Action.model_validate_json(payload)
    if action.action == "fill":
        return f"page.get_by_test_id({action.bid!r}).fill({action.text!r}, timeout=5000)"
    if action.action == "click_benchmark_link":
        return (f"_benchmark_link = page.get_by_test_id({action.bid!r})\n"
                f"if not _benchmark_link.evaluate({LINK_PREDICATE_JS!r}):\n"
                "    raise ValueError('Target is not a visible allowlisted benchmark link')\n"
                "_benchmark_link.click(timeout=5000)")
    if action.action == "activate_tab":
        return (
            f"_tab_target = page.get_by_test_id({action.bid!r})\n"
            "if not _tab_target.evaluate(\"(el) => el.getAttribute('role') === 'tab' && "
            "!!el.closest('[role=tablist]') && !!el.getAttribute('aria-controls') && "
            "!!document.getElementById(el.getAttribute('aria-controls'))\"):\n"
            "    raise ValueError('Tab target lacks an associated panel')\n"
            "_tab_anchor = _tab_target.locator('a.ui-tabs-anchor')\n"
            "if _tab_anchor.count() == 1:\n"
            "    if _tab_anchor.get_attribute('href') != '#' + _tab_target.get_attribute('aria-controls'):\n"
            "        raise ValueError('Tab anchor does not match controlled panel')\n"
            "    _tab_anchor.click(timeout=5000)\n"
            "elif _tab_anchor.count() == 0:\n"
            "    _tab_target.click(timeout=5000)\n"
            "else:\n"
            "    raise ValueError('Ambiguous tab anchor')"
        )
    if action.action in ("set_checked", "check_radio", "select_option"):
        native = {"set_checked": "el.tagName === 'INPUT' && el.type === 'checkbox'",
                  "check_radio": "el.tagName === 'INPUT' && el.type === 'radio'",
                  "select_option": "el.tagName === 'SELECT' && !el.multiple"}[action.action]
        operation = {"set_checked": f"set_checked({action.checked!r}, timeout=5000)",
                     "check_radio": "check(timeout=5000)",
                     "select_option": f"select_option(label={action.text!r}, timeout=5000)"}[action.action]
        return (f"_selection_target = page.get_by_test_id({action.bid!r})\n"
                f"if not _selection_target.evaluate({('(el) => ' + native)!r}):\n"
                "    raise ValueError('Selection target has incompatible native type')\n"
                f"_selection_target.{operation}")
    return f"page.get_by_test_id({action.bid!r}).click(timeout=5000)"
