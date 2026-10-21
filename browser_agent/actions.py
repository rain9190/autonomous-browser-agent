import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClickAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["click"]
    bid: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["click", "fill"]
    bid: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    text: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def check_text(self):
        if self.action == "fill" and (self.text is None or self.text == ""):
            raise ValueError("Fill requires nonempty text")
        if self.action == "click" and self.text is not None:
            raise ValueError("Click must have null text")
        return self


def button_ids(tree: str) -> set[str]:
    # IDs and roles come from BrowserGym's accessibility tree, not model claims.
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] button\b", tree))


def textbox_ids(tree: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*\[([A-Za-z0-9_-]{1,64})\] textbox\b", tree))


def validate_action(raw: object, allowed: set[str], editable: set[str] | None = None) -> Action:
    action = Action.model_validate(raw)
    targets = allowed if action.action == "click" else (editable or set())
    if action.bid not in targets:
        raise ValueError("The selected ID does not match the observed action role")
    return action


def action_mapping(payload: str) -> str:
    # BrowserGym requires Python internally. Generate only this fixed template
    # from validated JSON; never forward model-generated Python to BrowserGym.
    action = Action.model_validate_json(payload)
    if action.action == "fill":
        return f"page.get_by_test_id({action.bid!r}).fill({action.text!r}, timeout=5000)"
    return f"page.get_by_test_id({action.bid!r}).click(timeout=5000)"
