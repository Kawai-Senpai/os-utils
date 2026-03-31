from __future__ import annotations

from pathlib import Path
from typing import Optional

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd, run_powershell
from os_utils.core.safety import confirm_sensitive, require_admin


def _windows_install() -> None:
    run_powershell("Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0")
    run_powershell("Start-Service sshd")
    run_powershell("Set-Service -Name sshd -StartupType Automatic")


def _windows_status() -> None:
    run_powershell("Get-Service sshd")


def _linux_service_name() -> Optional[str]:
    for name in ("ssh", "sshd"):
        result = run_cmd(["systemctl", "status", name, "--no-pager"])
        if result.ok:
            return name
    return None


def _linux_install(ctx: AppContext) -> None:
    pm = ctx.platform.package_manager
    if pm == "apt":
        run_cmd(["apt", "update"], use_sudo=True)
        run_cmd(["apt", "install", "-y", "openssh-server"], use_sudo=True)
    elif pm == "dnf":
        run_cmd(["dnf", "install", "-y", "openssh-server"], use_sudo=True)
    elif pm == "pacman":
        run_cmd(["pacman", "-S", "--noconfirm", "openssh"], use_sudo=True)


def _linux_enable(service: str) -> None:
    run_cmd(["systemctl", "enable", "--now", service], use_sudo=True)


def _linux_disable_socket_enable_service() -> None:
    run_cmd(["systemctl", "disable", "--now", "ssh.socket"], use_sudo=True)
    run_cmd(["systemctl", "enable", "--now", "ssh.service"], use_sudo=True)


def _linux_socket_status() -> tuple[bool, bool]:
    socket_enabled = run_cmd(["systemctl", "is-enabled", "ssh.socket"], use_sudo=True)
    service_enabled = run_cmd(["systemctl", "is-enabled", "ssh.service"], use_sudo=True)
    return socket_enabled.ok, service_enabled.ok


def _linux_write_sshd_snippet(port: str, password_auth: str) -> bool:
    path = Path("/etc/ssh/sshd_config.d/99-os-utils.conf")
    backup = Path("/etc/ssh/sshd_config.d/99-os-utils.conf.bak")
    if path.exists():
        run_cmd(["cp", str(path), str(backup)], use_sudo=True)

    content = f"Port {port}\nPasswordAuthentication {password_auth}\n"
    tmp = Path("/tmp/os-utils-sshd.conf")
    tmp.write_text(content, encoding="utf-8")
    if not run_cmd(["cp", str(tmp), str(path)], use_sudo=True).ok:
        return False
    test = run_cmd(["sshd", "-t"], use_sudo=True)
    if test.ok:
        return True

    if backup.exists():
        run_cmd(["cp", str(backup), str(path)], use_sudo=True)
    else:
        run_cmd(["rm", "-f", str(path)], use_sudo=True)
    return False


def menu(ctx: AppContext) -> None:
    console = ctx.console
    options = [
        "Install OpenSSH server",
        "Enable/start SSH",
        "Stop SSH",
        "Show SSH status",
        "Switch to classic service mode (Ubuntu)",
        "Configure port and password auth",
    ]
    while True:
        choice = select_from_list(console, "SSH options", options)
        if choice is None:
            return

        if is_windows():
            if choice == 0:
                if not require_admin(console, ctx.platform, "Installing OpenSSH"):
                    pause(console)
                    continue
                if not confirm_sensitive(console, "Install OpenSSH server on Windows?"):
                    continue
                _windows_install()
                console.success("OpenSSH server install command issued.")
                pause(console)
                continue

            if choice == 1:
                if not require_admin(console, ctx.platform, "Starting OpenSSH"):
                    pause(console)
                    continue
                run_powershell("Start-Service sshd")
                run_powershell("Set-Service -Name sshd -StartupType Automatic")
                console.success("sshd started.")
                pause(console)
                continue

            if choice == 2:
                if not require_admin(console, ctx.platform, "Stopping OpenSSH"):
                    pause(console)
                    continue
                run_powershell("Stop-Service sshd")
                console.success("sshd stopped.")
                pause(console)
                continue

            if choice == 3:
                console.info(run_powershell("Get-Service sshd").stdout.strip())
                pause(console)
                continue

            if choice == 4:
                console.warn("Socket mode is not applicable on Windows.")
                pause(console)
                continue

            if choice == 5:
                console.warn("Windows SSH config editing is not automated in this tool.")
                pause(console)
                continue

        if not require_admin(console, ctx.platform, "SSH management"):
            pause(console)
            continue

        service = _linux_service_name() or "ssh"

        if choice == 0:
            if not confirm_sensitive(console, "Install OpenSSH server?"):
                continue
            _linux_install(ctx)
            console.success("OpenSSH install command issued.")
            pause(console)
            continue

        if choice == 1:
            _linux_enable(service)
            console.success("SSH enabled and started.")
            pause(console)
            continue

        if choice == 2:
            run_cmd(["systemctl", "stop", service], use_sudo=True)
            console.success("SSH stopped.")
            pause(console)
            continue

        if choice == 3:
            result = run_cmd(["systemctl", "status", service, "--no-pager"], use_sudo=True)
            console.info(result.stdout.strip() or result.stderr.strip())
            pause(console)
            continue

        if choice == 4:
            socket_enabled, service_enabled = _linux_socket_status()
            console.info(f"ssh.socket enabled: {'yes' if socket_enabled else 'no'}")
            console.info(f"ssh.service enabled: {'yes' if service_enabled else 'no'}")
            if not confirm_sensitive(console, "Switch to classic ssh.service mode?"):
                continue
            _linux_disable_socket_enable_service()
            console.success("Switched to classic service mode.")
            pause(console)
            continue

        if choice == 5:
            port = prompt_text(console, "SSH port", default="22")
            password_auth = "yes" if confirm(console, "Allow password auth?", default=False) else "no"
            if not confirm_sensitive(console, f"Update sshd config to Port {port}?"):
                continue
            ok = _linux_write_sshd_snippet(port, password_auth)
            if not ok:
                console.warn("Failed to update sshd config.")
                pause(console)
                continue
            run_cmd(["systemctl", "restart", service], use_sudo=True)
            console.success("sshd config updated.")
            pause(console)
