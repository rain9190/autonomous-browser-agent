
import re

import gymnasium as gym
import browsergym.miniwob  # Registers MiniWoB environments
from browsergym.utils.obs import flatten_axtree_to_str


TASK_ID = "browsergym/miniwob.click-test"
SEED = 42


def main() -> None:
    env = gym.make(TASK_ID, headless=True)

    try:
        observation, info = env.reset(seed=SEED)

        print("TASK:", TASK_ID)
        print("GOAL:", observation["goal"])
        print("URL:", observation["url"])
        print("\nACCESSIBILITY TREE:\n")

        tree = flatten_axtree_to_str(
            observation["axtree_object"]
        )
        print(tree[:8000])

        bid = input(
            "\nEnter the button's [bid] from the tree: "
        ).strip()

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", bid):
            raise ValueError("Invalid browser element ID")

        # The identifier is validated and quoted safely.
        action = f"click({bid!r})"
        print("\nACTION:", action)

        observation, reward, terminated, truncated, info = (
            env.step(action)
        )

        error = observation["last_action_error"]

        print("REWARD:", reward)
        print("TERMINATED:", terminated)
        print("TRUNCATED:", truncated)
        print("ACTION ERROR:", error or "None")

        if error:
            raise RuntimeError(error)

        print("\nBrowser action executed without an error.")

        if reward > 0 and terminated:
            print("Benchmark confirms task success.")
        else:
            print("Task success not confirmed.")

    finally:
        env.close()


if __name__ == "__main__":
    main()
