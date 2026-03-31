from __future__ import annotations

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive, require_admin


def _run_and_show(console, result) -> None:
    if result.ok:
        console.info(result.stdout.strip() or "(no output)")
    else:
        console.warn(result.stderr.strip() or "Command failed.")


def _windows_menu(ctx: AppContext, choice: int) -> None:
    console = ctx.console
    if not run_cmd(["winget", "--version"]).ok:
        console.warn("winget is not available on this system.")
        return
    if choice == 0:
        _run_and_show(console, run_cmd(["winget", "list"]))
        return
    if choice == 1:
        term = prompt_text(console, "Search term")
        _run_and_show(console, run_cmd(["winget", "search", term]))
        return
    if choice == 2:
        if not require_admin(console, ctx.platform, "Installing packages"):
            return
        package = prompt_text(console, "Package name or id")
        if not confirm_sensitive(console, f"Install {package} via winget?"):
            return
        _run_and_show(console, run_cmd(["winget", "install", package]))
        return
    if choice == 3:
        if not require_admin(console, ctx.platform, "Uninstalling packages"):
            return
        package = prompt_text(console, "Package name or id")
        if not confirm_sensitive(console, f"Uninstall {package} via winget?"):
            return
        _run_and_show(console, run_cmd(["winget", "uninstall", package]))


def _linux_menu(ctx: AppContext, choice: int) -> None:
    console = ctx.console
    pm = ctx.platform.package_manager
    if pm is None:
        console.warn("No supported package manager detected.")
        return

    if choice == 0:
        if pm == "apt":
            _run_and_show(console, run_cmd(["apt", "list", "--installed"]))
        elif pm == "dnf":
            _run_and_show(console, run_cmd(["dnf", "list", "--installed"]))
        else:
            _run_and_show(console, run_cmd(["pacman", "-Qe"]))
        return

    if choice == 1:
        term = prompt_text(console, "Search term")
        if pm == "apt":
            _run_and_show(console, run_cmd(["apt", "search", term]))
        elif pm == "dnf":
            _run_and_show(console, run_cmd(["dnf", "search", term]))
        else:
            _run_and_show(console, run_cmd(["pacman", "-Ss", term]))
        return

    if choice == 2:
        if not require_admin(console, ctx.platform, "Installing packages"):
            return
        package = prompt_text(console, "Package name")
        if not confirm_sensitive(console, f"Install {package}?"):
            return
        if pm == "apt":
            _run_and_show(console, run_cmd(["apt", "install", "-y", package], use_sudo=True))
        elif pm == "dnf":
            _run_and_show(console, run_cmd(["dnf", "install", "-y", package], use_sudo=True))
        else:
            _run_and_show(console, run_cmd(["pacman", "-S", "--noconfirm", package], use_sudo=True))
        return

    if choice == 3:
        if not require_admin(console, ctx.platform, "Uninstalling packages"):
            return
        package = prompt_text(console, "Package name")
        if not confirm_sensitive(console, f"Remove {package}?"):
            return
        if pm == "apt":
            purge = confirm(console, "Purge config files?", default=False)
            cmd = ["apt", "purge", "-y", package] if purge else ["apt", "remove", "-y", package]
            _run_and_show(console, run_cmd(cmd, use_sudo=True))
        elif pm == "dnf":
            _run_and_show(console, run_cmd(["dnf", "remove", "-y", package], use_sudo=True))
        else:
            _run_and_show(console, run_cmd(["pacman", "-Rns", "--noconfirm", package], use_sudo=True))


def menu(ctx: AppContext) -> None:
    options = [
        "List installed packages",
        "Search packages",
        "Install package",
        "Uninstall package",
    ]

    while True:
        choice = select_from_list(ctx.console, "Package options", options)
        if choice is None:
            return

        if is_windows():
            _windows_menu(ctx, choice)
        else:
            _linux_menu(ctx, choice)
        pause(ctx.console)
