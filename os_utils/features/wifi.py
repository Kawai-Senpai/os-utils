from typing import List, Optional

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import pause, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive


def _windows_list_profiles() -> List[str]:
    result = run_cmd(["netsh", "wlan", "show", "profiles"])
    profiles: List[str] = []
    for line in result.stdout.splitlines():
        if "Profile" in line and ":" in line:
            name = line.split(":", 1)[1].strip()
            if name:
                profiles.append(name)
    return sorted(set(profiles))


def _windows_active_ssid() -> Optional[str]:
    result = run_cmd(["netsh", "wlan", "show", "interfaces"])
    for line in result.stdout.splitlines():
        if line.strip().startswith("SSID") and ":" in line:
            value = line.split(":", 1)[1].strip()
            if value and value != "<none>":
                return value
    return None


def _windows_get_password(profile: str) -> Optional[str]:
    result = run_cmd(["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"])
    for line in result.stdout.splitlines():
        if "Key Content" in line and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def _linux_list_profiles() -> List[str]:
    result = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    profiles: List[str] = []
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        name, conn_type = line.split(":", 1)
        if conn_type in {"wifi", "802-11-wireless"}:
            profiles.append(name)
    return sorted(set(profiles))


def _linux_active_profile() -> Optional[str]:
    result = run_cmd(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 3:
            name, conn_type, _device = parts[0], parts[1], parts[2]
            if conn_type in {"wifi", "802-11-wireless"}:
                return name
    return None


def _linux_get_password(profile: str) -> Optional[str]:
    result = run_cmd(["nmcli", "--show-secrets", "connection", "show", profile])
    for line in result.stdout.splitlines():
        if "802-11-wireless-security.psk" in line and ":" in line:
            return line.split(":", 1)[1].strip() or None
    return None


def menu(ctx: AppContext) -> None:
    console = ctx.console

    if is_windows():
        is_supported = True
    else:
        is_supported = ctx.platform.has_networkmanager

    if not is_supported:
        console.warn("Wi-Fi password lookup requires NetworkManager on Linux.")
        return

    if not confirm_sensitive(console, "This will reveal saved Wi-Fi secrets. Continue?"):
        return

    options = [
        "List Wi-Fi profiles",
        "Show password for a profile",
        "Show password for active Wi-Fi",
    ]

    while True:
        choice = select_from_list(console, "Wi-Fi options", options)
        if choice is None:
            return

        if is_windows():
            profiles = _windows_list_profiles()
            if choice == 0:
                console.info("Saved Wi-Fi profiles:")
                for profile in profiles:
                    print(f"- {profile}")
                pause(console)
                continue

            if choice == 1:
                if not profiles:
                    console.warn("No Wi-Fi profiles found.")
                    pause(console)
                    continue
                idx = select_from_list(console, "Select profile", profiles)
                if idx is None:
                    continue
                profile = profiles[idx]
                password = _windows_get_password(profile)
                if password:
                    console.success(f"Password for {profile}: {password}")
                else:
                    console.warn("No password found or access denied.")
                pause(console)
                continue

            if choice == 2:
                ssid = _windows_active_ssid()
                if not ssid:
                    console.warn("No active Wi-Fi connection detected.")
                    pause(console)
                    continue
                password = _windows_get_password(ssid)
                if password:
                    console.success(f"Password for {ssid}: {password}")
                else:
                    console.warn("No password found or access denied.")
                pause(console)
                continue

        profiles = _linux_list_profiles()
        if choice == 0:
            console.info("Saved Wi-Fi profiles:")
            for profile in profiles:
                print(f"- {profile}")
            pause(console)
            continue

        if choice == 1:
            if not profiles:
                console.warn("No Wi-Fi profiles found.")
                pause(console)
                continue
            idx = select_from_list(console, "Select profile", profiles)
            if idx is None:
                continue
            profile = profiles[idx]
            password = _linux_get_password(profile)
            if password:
                console.success(f"Password for {profile}: {password}")
            else:
                console.warn("No password found or access denied.")
            pause(console)
            continue

        if choice == 2:
            profile = _linux_active_profile()
            if not profile:
                console.warn("No active Wi-Fi connection detected.")
                pause(console)
                continue
            password = _linux_get_password(profile)
            if password:
                console.success(f"Password for {profile}: {password}")
            else:
                console.warn("No password found or access denied.")
            pause(console)
