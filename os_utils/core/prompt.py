from typing import Iterable, List, Optional

from os_utils.core.console import Console


def prompt_text(
    console: Console,
    label: str,
    default: Optional[str] = None,
    allow_empty: bool = False,
) -> str:
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value or allow_empty:
            return value
        console.warn("Please enter a value.")


def confirm(console: Console, label: str, default: bool = False) -> bool:
    prompt = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"{label} {prompt}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        console.warn("Please answer yes or no.")


def select_from_list(
    console: Console,
    label: str,
    options: Iterable[str],
    allow_back: bool = True,
) -> Optional[int]:
    choices: List[str] = list(options)
    if not choices:
        console.warn("No options available.")
        return None

    console.section(label)
    for idx, item in enumerate(choices, start=1):
        color = "lgray" if idx % 2 == 0 else "cyan"
        console.paint(f"  [{idx}] {item}", color=color)
    if allow_back:
        console.paint("  [0] Back", color="dgray")

    while True:
        raw = input("Select: ").strip()
        if allow_back and raw == "0":
            return None
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return idx - 1
        console.warn("Invalid selection.")


def pause(console: Console, label: str = "Press Enter to continue...") -> None:
    input(label)
