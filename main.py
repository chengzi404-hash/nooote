import ctypes
import os
import sys

from nooote import create_app

REPO_URL = "https://github.com/chengzi404-hash/nooote"
AUTHOR = "chengzi404-hash"
BLUE_BOLD = "\033[1;34m"
RESET = "\033[0m"

BANNER = r"""
                         _
 _ __   ___   ___   ___ | |_ ___
| '_ \ / _ \ / _ \ / _ \| __/ _ \
| | | | (_) | (_) | (_) | ||  __/
|_| |_|\___/ \___/ \___/ \__\___|
"""


def enable_ansi() -> None:
    if os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)


def print_banner() -> None:
    text = (
        f"{BANNER.rstrip()}\n"
        f"Repository: {REPO_URL}\n"
        f"Author:     {AUTHOR}"
    )
    if sys.stdout.isatty() and not os.environ.get("NO_COLOR"):
        enable_ansi()
        print(f"{BLUE_BOLD}{text}{RESET}")
    else:
        print(text)


app = create_app()

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    print_banner()


if __name__ == "__main__":
    app.run(port=5000)
