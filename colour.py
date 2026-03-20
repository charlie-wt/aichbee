from typing import Callable


def _from_esc_code(esc: str) -> Callable[[str], str]:
    def fn(text: str) -> str:
        return esc + text + "\033[0m"
    return fn


grey = _from_esc_code("\033[90m")
