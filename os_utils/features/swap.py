from __future__ import annotations

import os
from pathlib import Path

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive, require_admin


def _swap_status() -> str:
    result = run_cmd(["bash", "-lc", "free -h && echo '' && cat /proc/swaps"])
    return result.stdout.strip() if result.ok else result.stderr.strip()


def _is_btrfs() -> bool:
    result = run_cmd(["stat", "-f", "-c", "%T", "/"])
    return result.ok and result.stdout.strip() == "btrfs"


def _swapfile_exists(path: Path) -> bool:
    return path.exists()


def _create_swapfile(path: Path, size_gb: int) -> bool:
    size_arg = f"{size_gb}G"
    result = run_cmd(["fallocate", "-l", size_arg, str(path)], use_sudo=True)
    if not result.ok:
        size_mb = size_gb * 1024
        result = run_cmd(
            ["dd", "if=/dev/zero", f"of={path}", "bs=1M", f"count={size_mb}"],
            use_sudo=True,
        )
        if not result.ok:
            return False
    if not run_cmd(["chmod", "600", str(path)], use_sudo=True).ok:
        return False
    if not run_cmd(["mkswap", str(path)], use_sudo=True).ok:
        return False
    if not run_cmd(["swapon", str(path)], use_sudo=True).ok:
        return False
    fstab_line = f"{path} none swap sw 0 0"
    run_cmd(["bash", "-lc", f"grep -q '{path}' /etc/fstab || echo '{fstab_line}' >> /etc/fstab"], use_sudo=True)
    return True


def _remove_swapfile(path: Path) -> bool:
    run_cmd(["swapoff", str(path)], use_sudo=True)
    run_cmd(["bash", "-lc", f"sed -i '\\|{path}|d' /etc/fstab"], use_sudo=True)
    result = run_cmd(["rm", "-f", str(path)], use_sudo=True)
    return result.ok


def menu(ctx: AppContext) -> None:
    console = ctx.console
    if is_windows():
        console.warn("Swap management is only supported on Linux.")
        return

    options = ["Show swap status", "Create swap file", "Remove swap file"]

    while True:
        choice = select_from_list(console, "Swap options", options)
        if choice is None:
            return

        if choice == 0:
            console.info(_swap_status())
            pause(console)
            continue

        if not require_admin(console, ctx.platform, "Managing swap"):
            pause(console)
            continue

        swap_path = Path("/swapfile")
        if choice == 1:
            if _swapfile_exists(swap_path):
                console.warn("/swapfile already exists.")
                pause(console)
                continue
            if _is_btrfs():
                console.warn("Btrfs detected. Swap files need special setup on Btrfs.")
                if not confirm(console, "Continue anyway?", default=False):
                    continue
            size_text = prompt_text(console, "Swap size in GB", default="4")
            if not size_text.isdigit():
                console.warn("Invalid size.")
                pause(console)
                continue
            size_gb = int(size_text)
            if size_gb <= 0:
                console.warn("Size must be greater than zero.")
                pause(console)
                continue
            if not confirm_sensitive(console, f"Create {size_gb}G swap file at /swapfile?"):
                continue
            ok = _create_swapfile(swap_path, size_gb)
            console.success("Swap file created.") if ok else console.warn("Failed to create swap file.")
            pause(console)
            continue

        if choice == 2:
            if not _swapfile_exists(swap_path):
                console.warn("/swapfile not found.")
                pause(console)
                continue
            if not confirm_sensitive(console, "Remove /swapfile and disable swap?"):
                continue
            ok = _remove_swapfile(swap_path)
            console.success("Swap file removed.") if ok else console.warn("Failed to remove swap file.")
            pause(console)
