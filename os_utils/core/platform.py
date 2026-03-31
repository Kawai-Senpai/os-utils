from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from os_utils.core.console import Console
from os_utils.core.runner import run_cmd


@dataclass
class PlatformInfo:
    os_label: str
    distro_id: Optional[str]
    distro_like: List[str]
    version_id: Optional[str]
    package_manager: Optional[str]
    init_system: Optional[str]
    has_systemd: bool
    has_networkmanager: bool
    has_resolved: bool
    is_admin: bool


def is_windows() -> bool:
    return os.name == "nt"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_admin() -> bool:
    if is_windows():
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    return False


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def read_os_release() -> Dict[str, str]:
    data: Dict[str, str] = {}
    path = "/etc/os-release"
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key] = value.strip().strip('"')
    return data


def detect_platform(console: Console) -> PlatformInfo:
    if is_windows():
        return PlatformInfo(
            os_label="Windows",
            distro_id=None,
            distro_like=[],
            version_id=None,
            package_manager="winget" if has_command("winget") else None,
            init_system=None,
            has_systemd=False,
            has_networkmanager=False,
            has_resolved=False,
            is_admin=is_admin(),
        )

    distro = read_os_release()
    distro_id = distro.get("ID")
    distro_like = distro.get("ID_LIKE", "").split() if distro.get("ID_LIKE") else []
    version_id = distro.get("VERSION_ID")

    init_system = None
    if os.path.exists("/proc/1/comm"):
        with open("/proc/1/comm", "r", encoding="utf-8") as handle:
            init_system = handle.read().strip()

    has_systemd = init_system == "systemd"
    package_manager = None
    if has_command("apt"):
        package_manager = "apt"
    elif has_command("dnf"):
        package_manager = "dnf"
    elif has_command("pacman"):
        package_manager = "pacman"

    has_networkmanager = False
    if has_command("nmcli") and has_systemd and has_command("systemctl"):
        nm_state = run_cmd(["systemctl", "is-active", "NetworkManager"])
        has_networkmanager = nm_state.ok and nm_state.stdout.strip() == "active"

    has_resolved = False
    if has_systemd and has_command("systemctl"):
        resolved_state = run_cmd(["systemctl", "is-active", "systemd-resolved"])
        has_resolved = resolved_state.ok and resolved_state.stdout.strip() == "active"

    return PlatformInfo(
        os_label="Linux",
        distro_id=distro_id,
        distro_like=distro_like,
        version_id=version_id,
        package_manager=package_manager,
        init_system=init_system,
        has_systemd=has_systemd,
        has_networkmanager=has_networkmanager,
        has_resolved=has_resolved,
        is_admin=is_admin(),
    )
