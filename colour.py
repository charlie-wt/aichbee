from typing import Callable


# Note: doesn't allow nesting calls
def _from_esc_code(esc: str) -> Callable[[str], str]:
    def fn(text: str) -> str:
        return esc + text + "\033[0m"
    return fn


black = _from_esc_code("\033[30m")
red = _from_esc_code("\033[31m")
green = _from_esc_code("\033[32m")
yellow = _from_esc_code("\033[33m")
blue = _from_esc_code("\033[34m")
magenta = _from_esc_code("\033[35m")
cyan = _from_esc_code("\033[36m")
white = _from_esc_code("\033[37m")
default = _from_esc_code("\033[39m")

bright_black = _from_esc_code("\033[90m")
bright_red = _from_esc_code("\033[91m")
bright_green = _from_esc_code("\033[92m")
bright_yellow = _from_esc_code("\033[93m")
bright_blue = _from_esc_code("\033[94m")
bright_magenta = _from_esc_code("\033[95m")
bright_cyan = _from_esc_code("\033[96m")
bright_white = _from_esc_code("\033[97m")

grey = bright_black
