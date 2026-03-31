from __future__ import annotations

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd, run_powershell
from os_utils.core.safety import confirm_sensitive, require_admin


def _show(console, result) -> None:
    if result.ok:
        console.info(result.stdout.strip() or "(no output)")
    else:
        console.warn(result.stderr.strip() or "Command failed.")


def _windows_processes(console) -> None:
    script = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 50"
    _show(console, run_powershell(script))


def _linux_processes(console) -> None:
    _show(console, run_cmd(["bash", "-lc", "ps aux --sort=-%cpu | head -n 30"]))


def _windows_services(console) -> None:
    script = "Get-Service | Sort-Object Status, DisplayName"
    _show(console, run_powershell(script))


def _linux_services(console) -> None:
    _show(console, run_cmd(["systemctl", "list-units", "--type=service", "--all"]))


def _windows_listeners(console) -> None:
    script = "Get-NetTCPConnection -State Listen | Select-Object -First 50"
    _show(console, run_powershell(script))


def _linux_listeners(console) -> None:
    _show(console, run_cmd(["ss", "-lntup"]))


def _windows_scheduled_tasks(console) -> None:
    _show(console, run_cmd(["schtasks", "/query", "/fo", "LIST", "/v"]))


def _linux_timers(console) -> None:
    _show(console, run_cmd(["systemctl", "list-timers", "--all"]))


def _kill_process(ctx: AppContext) -> None:
    console = ctx.console
    if not require_admin(console, ctx.platform, "Killing processes"):
        return
    pid = prompt_text(console, "PID")
    if not pid.isdigit():
        console.warn("Invalid PID.")
        return
    if not confirm_sensitive(console, f"Force kill PID {pid}?"):
        return
    if is_windows():
        script = f"Stop-Process -Id {pid} -Force"
        _show(console, run_powershell(script))
    else:
        _show(console, run_cmd(["kill", "-9", pid], use_sudo=True))


def menu(ctx: AppContext) -> None:
    options = [
        "List running processes",
        "List services",
        "List listening ports",
        "List scheduled tasks or timers",
        "Kill process by PID",
    ]

    while True:
        choice = select_from_list(ctx.console, "Process options", options)
        if choice is None:
            return

        if choice == 0:
            _windows_processes(ctx.console) if is_windows() else _linux_processes(ctx.console)
            pause(ctx.console)
            continue
        if choice == 1:
            _windows_services(ctx.console) if is_windows() else _linux_services(ctx.console)
            pause(ctx.console)
            continue
        if choice == 2:
            _windows_listeners(ctx.console) if is_windows() else _linux_listeners(ctx.console)
            pause(ctx.console)
            continue
        if choice == 3:
            _windows_scheduled_tasks(ctx.console) if is_windows() else _linux_timers(ctx.console)
            pause(ctx.console)
            continue
        if choice == 4:
            _kill_process(ctx)
            pause(ctx.console)
