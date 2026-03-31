from __future__ import annotations

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd, run_powershell
from os_utils.core.safety import confirm_sensitive, require_admin


def _run(console, result) -> None:
    if result.ok:
        console.info(result.stdout.strip() or "(no output)")
    else:
        console.warn(result.stderr.strip() or "Command failed.")


def _windows_action(service: str, action: str):
    if action == "start":
        return run_powershell(f"Start-Service -Name '{service}'")
    if action == "stop":
        return run_powershell(f"Stop-Service -Name '{service}'")
    if action == "restart":
        return run_powershell(f"Restart-Service -Name '{service}'")
    if action == "enable":
        return run_powershell(f"Set-Service -Name '{service}' -StartupType Automatic")
    if action == "disable":
        return run_powershell(f"Set-Service -Name '{service}' -StartupType Disabled")
    if action == "status":
        return run_powershell(f"Get-Service -Name '{service}'")
    if action == "logs":
        return run_powershell(
            "Get-WinEvent -LogName System -MaxEvents 50 | "
            "Select-Object -First 50 | Format-List"
        )
    return run_powershell("Write-Output 'Unknown action'")


def _linux_action(service: str, action: str):
    if action == "start":
        return run_cmd(["systemctl", "start", service], use_sudo=True)
    if action == "stop":
        return run_cmd(["systemctl", "stop", service], use_sudo=True)
    if action == "restart":
        return run_cmd(["systemctl", "restart", service], use_sudo=True)
    if action == "enable":
        return run_cmd(["systemctl", "enable", service], use_sudo=True)
    if action == "disable":
        return run_cmd(["systemctl", "disable", service], use_sudo=True)
    if action == "status":
        return run_cmd(["systemctl", "status", service, "--no-pager"], use_sudo=True)
    if action == "logs":
        return run_cmd(["journalctl", "-u", service, "-n", "100", "--no-pager"], use_sudo=True)
    return run_cmd(["echo", "Unknown action"])


def menu(ctx: AppContext) -> None:
    options = [
        "Start service",
        "Stop service",
        "Restart service",
        "Enable on boot",
        "Disable on boot",
        "Show status",
        "Show logs",
    ]
    while True:
        choice = select_from_list(ctx.console, "Service control", options)
        if choice is None:
            return

        if not require_admin(ctx.console, ctx.platform, "Service control"):
            pause(ctx.console)
            continue

        service = prompt_text(ctx.console, "Service name (e.g., ssh, sshd, docker)")
        if not confirm_sensitive(ctx.console, f"Run '{options[choice]}' on {service}?"):
            continue

        action_map = {
            0: "start",
            1: "stop",
            2: "restart",
            3: "enable",
            4: "disable",
            5: "status",
            6: "logs",
        }
        action = action_map.get(choice)
        if action is None:
            continue

        result = _windows_action(service, action) if is_windows() else _linux_action(service, action)
        _run(ctx.console, result)
        pause(ctx.console)
