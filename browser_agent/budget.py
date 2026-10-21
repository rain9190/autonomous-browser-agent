from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    max_steps: int = 2

    def __post_init__(self):
        if type(self.max_steps) is not int or not 1 <= self.max_steps <= 6:
            raise ValueError("Action budget must be an integer from 1 to 6")

    @property
    def run_timeout(self):
        return max(90, 25 * self.max_steps + 15)
