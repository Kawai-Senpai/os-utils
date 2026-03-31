from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd, run_powershell
from os_utils.core.safety import confirm_sensitive, require_admin


def _entries(ctx: AppContext) -> List[Dict[str, str]]:
    return ctx.config.setdefault("startup_entries", [])


def _save_entry(ctx: AppContext, entry: Dict[str, str]) -> None:
    _entries(ctx).append(entry)


def _remove_entry(ctx: AppContext, idx: int) -> Dict[str, str]:
    entries = _entries(ctx)
    return entries.pop(idx)


def _windows_startup_folder(all_users: bool = False) -> Path:
    if all_users:
        return Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "StartUp"
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _windows_create_shortcut(name: str, target: str, all_users: bool) -> Path:
    folder = _windows_startup_folder(all_users)
    folder.mkdir(parents=True, exist_ok=True)
    lnk_path = folder / f"{name}.lnk"
    script = (
        f"$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{lnk_path}'); "
        f"$shortcut.TargetPath = '{target}'; "
        f"$shortcut.Save();"
    )
    run_powershell(script)
    return lnk_path


def _windows_add_registry_run(name: str, target: str, all_users: bool) -> None:
    hive = "HKLM" if all_users else "HKCU"
    key = f"{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    cmd = ["reg", "add", key, "/v", name, "/d", target, "/f"]
    run_cmd(cmd)


def _windows_add_task(name: str, target: str, on_startup: bool) -> None:
    task_name = f"os-utils\\{name}"
    trigger = "ONSTART" if on_startup else "ONLOGON"
    run_as = "SYSTEM" if on_startup else os.environ.get("USERNAME", "")
    cmd = f'schtasks /create /tn "{task_name}" /sc {trigger} /tr "{target}" /ru "{run_as}" /f'
    run_cmd(cmd, shell=True)


def _windows_remove_entry(entry: Dict[str, str]) -> None:
    method = entry.get("method")
    if method == "startup_folder":
        lnk_path = entry.get("lnk_path")
        if lnk_path:
            run_cmd(["cmd", "/c", "del", "/f", lnk_path])
        return
    if method == "registry_run":
        hive = entry.get("hive", "HKCU")
        key = f"{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        run_cmd(["reg", "delete", key, "/v", entry.get("name", ""), "/f"])
        return
    if method in {"task_logon", "task_start"}:
        task_name = entry.get("task_name")
        if task_name:
            run_cmd(["schtasks", "/delete", "/tn", task_name, "/f"])
        return


def _linux_write_desktop(name: str, exec_cmd: str) -> Path:
    dest = Path.home() / ".config" / "autostart"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{name}.desktop"
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={name}\n"
        f"Exec={exec_cmd}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _linux_write_systemd_service(name: str, exec_cmd: str, user_service: bool) -> Path:
    if user_service:
        dest = Path.home() / ".config" / "systemd" / "user"
    else:
        dest = Path("/etc/systemd/system")
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{name}.service"
    content = (
        "[Unit]\n"
        f"Description={name} (os-utils)\n\n"
        "[Service]\n"
        f"ExecStart={exec_cmd}\n"
        "Restart=on-failure\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    if user_service:
        path.write_text(content, encoding="utf-8")
    else:
        tmp = Path("/tmp/os-utils.service")
        tmp.write_text(content, encoding="utf-8")
        run_cmd(["cp", str(tmp), str(path)], use_sudo=True)
    return path


def _linux_enable_service(name: str, user_service: bool) -> None:
    if user_service:
        run_cmd(["systemctl", "--user", "daemon-reload"])
        run_cmd(["systemctl", "--user", "enable", "--now", f"{name}.service"])
    else:
        run_cmd(["systemctl", "daemon-reload"], use_sudo=True)
        run_cmd(["systemctl", "enable", "--now", f"{name}.service"], use_sudo=True)


def _linux_remove_entry(entry: Dict[str, str]) -> None:
    method = entry.get("method")
    name = entry.get("name", "")
    if method == "autostart":
        path = entry.get("path")
        if path:
            run_cmd(["rm", "-f", path])
        return
    if method == "systemd_user":
        run_cmd(["systemctl", "--user", "disable", "--now", f"{name}.service"])
        path = entry.get("path")
        if path:
            run_cmd(["rm", "-f", path])
        return
    if method == "systemd_system":
        run_cmd(["systemctl", "disable", "--now", f"{name}.service"], use_sudo=True)
        path = entry.get("path")
        if path:
            run_cmd(["rm", "-f", path], use_sudo=True)
        return


def _add_startup_windows(ctx: AppContext) -> None:
    console = ctx.console
    name = prompt_text(console, "Entry name")
    target = prompt_text(console, "Command or script path")

    methods = [
        "Startup folder shortcut",
        "Registry Run (current user)",
        "Scheduled Task at logon",
        "Scheduled Task at system boot",
    ]
    idx = select_from_list(console, "Choose startup method", methods)
    if idx is None:
        return

    if not confirm_sensitive(console, f"Create startup entry '{name}'?"):
        return

    if idx == 0:
        all_users = confirm(console, "All users?", default=False)
        lnk_path = _windows_create_shortcut(name, target, all_users)
        _save_entry(
            ctx,
            {
                "os": "windows",
                "method": "startup_folder",
                "name": name,
                "lnk_path": str(lnk_path),
                "target": target,
            },
        )
        console.success("Startup shortcut created.")
        return

    if idx == 1:
        all_users = confirm(console, "All users?", default=False)
        _windows_add_registry_run(name, target, all_users)
        _save_entry(
            ctx,
            {
                "os": "windows",
                "method": "registry_run",
                "name": name,
                "target": target,
                "hive": "HKLM" if all_users else "HKCU",
            },
        )
        console.success("Registry Run entry created.")
        return

    if idx == 2:
        _windows_add_task(name, target, on_startup=False)
        _save_entry(
            ctx,
            {
                "os": "windows",
                "method": "task_logon",
                "name": name,
                "target": target,
                "task_name": f"os-utils\\{name}",
            },
        )
        console.success("Scheduled task created.")
        return

    if idx == 3:
        _windows_add_task(name, target, on_startup=True)
        _save_entry(
            ctx,
            {
                "os": "windows",
                "method": "task_start",
                "name": name,
                "target": target,
                "task_name": f"os-utils\\{name}",
            },
        )
        console.success("Scheduled task created.")


def _add_startup_linux(ctx: AppContext) -> None:
    console = ctx.console
    name = prompt_text(console, "Entry name")
    exec_cmd = prompt_text(console, "Command to run")

    methods = [
        "Desktop autostart (.desktop)",
        "systemd user service",
        "systemd system service",
    ]
    idx = select_from_list(console, "Choose startup method", methods)
    if idx is None:
        return

    if idx == 2 and not require_admin(console, ctx.platform, "Creating system services"):
        return

    if not confirm_sensitive(console, f"Create startup entry '{name}'?"):
        return

    if idx == 0:
        path = _linux_write_desktop(name, exec_cmd)
        _save_entry(
            ctx,
            {
                "os": "linux",
                "method": "autostart",
                "name": name,
                "path": str(path),
                "command": exec_cmd,
            },
        )
        console.success("Autostart entry created.")
        return

    if idx == 1:
        path = _linux_write_systemd_service(name, exec_cmd, user_service=True)
        _linux_enable_service(name, user_service=True)
        if confirm(console, "Enable lingering so it runs without login?", default=False):
            run_cmd(["loginctl", "enable-linger", os.environ.get("USER", "")], use_sudo=True)
        _save_entry(
            ctx,
            {
                "os": "linux",
                "method": "systemd_user",
                "name": name,
                "path": str(path),
                "command": exec_cmd,
            },
        )
        console.success("User service created.")
        return

    if idx == 2:
        path = _linux_write_systemd_service(name, exec_cmd, user_service=False)
        _linux_enable_service(name, user_service=False)
        _save_entry(
            ctx,
            {
                "os": "linux",
                "method": "systemd_system",
                "name": name,
                "path": str(path),
                "command": exec_cmd,
            },
        )
        console.success("System service created.")


def _list_entries(ctx: AppContext) -> None:
    console = ctx.console
    entries = _entries(ctx)
    if not entries:
        console.warn("No startup entries tracked yet.")
        return
    console.info("Tracked startup entries:")
    for idx, entry in enumerate(entries, start=1):
        name = entry.get("name", "unknown")
        method = entry.get("method", "unknown")
        path = entry.get("path") or entry.get("lnk_path") or entry.get("task_name")
        print(f"{idx}) {name} [{method}] {path or ''}")


def _remove_entry_menu(ctx: AppContext) -> None:
    console = ctx.console
    entries = _entries(ctx)
    if not entries:
        console.warn("No startup entries tracked yet.")
        return
    labels = [f"{e.get('name', 'unknown')} ({e.get('method', 'unknown')})" for e in entries]
    idx = select_from_list(console, "Select entry to remove", labels)
    if idx is None:
        return
    entry = entries[idx]
    if not confirm_sensitive(console, f"Remove startup entry '{entry.get('name')}'?"):
        return
    if is_windows():
        _windows_remove_entry(entry)
    else:
        _linux_remove_entry(entry)
    _remove_entry(ctx, idx)
    console.success("Startup entry removed.")


def menu(ctx: AppContext) -> None:
    options = ["Add startup entry", "List startup entries", "Remove startup entry"]
    while True:
        choice = select_from_list(ctx.console, "Startup options", options)
        if choice is None:
            return

        if choice == 0:
            if is_windows():
                _add_startup_windows(ctx)
            else:
                _add_startup_linux(ctx)
            pause(ctx.console)
            continue

        if choice == 1:
            _list_entries(ctx)
            pause(ctx.console)
            continue

        if choice == 2:
            _remove_entry_menu(ctx)
            pause(ctx.console)
