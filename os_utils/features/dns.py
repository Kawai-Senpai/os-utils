from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, select_from_list
from os_utils.core.runner import run_cmd, run_powershell_json
from os_utils.core.safety import confirm_sensitive, require_admin

CLOUDFLARE_V4 = ["1.1.1.1", "1.0.0.1"]
CLOUDFLARE_V6 = ["2606:4700:4700::1111", "2606:4700:4700::1001"]


def _windows_dns_snapshot() -> List[Dict[str, str]]:
    script = (
        "Get-DnsClientServerAddress | "
        "Select-Object InterfaceAlias, AddressFamily, ServerAddresses"
    )
    result, payload = run_powershell_json(script)
    if not result.ok or payload is None:
        return []
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def _windows_interfaces() -> List[str]:
    snapshot = _windows_dns_snapshot()
    aliases = {item.get("InterfaceAlias") for item in snapshot if item.get("InterfaceAlias")}
    return sorted(aliases)


def _windows_set_dns(alias: str, ipv4: bool, ipv6: bool) -> bool:
    if ipv4:
        v4_list = ",".join(f'"{addr}"' for addr in CLOUDFLARE_V4)
        script = (
            f"Set-DnsClientServerAddress -InterfaceAlias \"{alias}\" "
            f"-AddressFamily IPv4 -ServerAddresses ({v4_list})"
        )
        result = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
        if not result.ok:
            return False
    if ipv6:
        v6_list = ",".join(f'"{addr}"' for addr in CLOUDFLARE_V6)
        script = (
            f"Set-DnsClientServerAddress -InterfaceAlias \"{alias}\" "
            f"-AddressFamily IPv6 -ServerAddresses ({v6_list})"
        )
        result = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
        if not result.ok:
            return False
    return True


def _windows_reset_dns(alias: str) -> bool:
    script = f"Set-DnsClientServerAddress -InterfaceAlias \"{alias}\" -ResetServerAddresses"
    result = run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
    return result.ok


def _nmcli_connections(active_only: bool = True) -> List[str]:
    args = ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show"]
    if active_only:
        args.append("--active")
    result = run_cmd(args)
    connections: List[str] = []
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2:
            name, conn_type = parts[0], parts[1]
            if conn_type in {"wifi", "802-11-wireless", "ethernet"}:
                connections.append(name)
    return sorted(set(connections))


def _nmcli_set_dns(conn: str, ipv4: bool, ipv6: bool) -> bool:
    args = ["nmcli", "connection", "modify", conn]
    if ipv4:
        args += ["ipv4.ignore-auto-dns", "yes", "ipv4.dns", " ".join(CLOUDFLARE_V4)]
    if ipv6:
        args += ["ipv6.ignore-auto-dns", "yes", "ipv6.dns", " ".join(CLOUDFLARE_V6)]
    result = run_cmd(args, use_sudo=True)
    if not result.ok:
        return False
    up = run_cmd(["nmcli", "connection", "up", conn], use_sudo=True)
    return up.ok


def _nmcli_reset_dns(conn: str) -> bool:
    args = [
        "nmcli",
        "connection",
        "modify",
        conn,
        "ipv4.ignore-auto-dns",
        "no",
        "ipv4.dns",
        "",
        "ipv6.ignore-auto-dns",
        "no",
        "ipv6.dns",
        "",
    ]
    result = run_cmd(args, use_sudo=True)
    if not result.ok:
        return False
    up = run_cmd(["nmcli", "connection", "up", conn], use_sudo=True)
    return up.ok


def _update_resolved_conf(console, dns: List[str]) -> bool:
    path = Path("/etc/systemd/resolved.conf")
    lines: List[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    if not any(line.strip().lower() == "[resolve]" for line in lines):
        lines.append("[Resolve]")

    def set_key(key: str, value: str) -> None:
        for idx, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[idx] = f"{key}={value}"
                return
        lines.append(f"{key}={value}")

    set_key("DNS", " ".join(dns))
    set_key("FallbackDNS", "")

    tmp_path = Path("/tmp/os-utils-resolved.conf")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = run_cmd(["cp", str(tmp_path), str(path)], use_sudo=True)
    if not result.ok:
        console.warn(result.stderr.strip() or "Failed to update resolved.conf")
        return False
    restart = run_cmd(["systemctl", "restart", "systemd-resolved"], use_sudo=True)
    return restart.ok


def _write_resolv_conf(console, dns: List[str]) -> bool:
    path = Path("/etc/resolv.conf")
    if path.is_symlink():
        console.warn("/etc/resolv.conf is a symlink and may be managed by another service.")
        if not confirm(console, "Overwrite it anyway?", default=False):
            return False
    content = "".join([f"nameserver {addr}\n" for addr in dns])
    tmp_path = Path("/tmp/os-utils-resolv.conf")
    tmp_path.write_text(content, encoding="utf-8")
    result = run_cmd(["cp", str(tmp_path), str(path)], use_sudo=True)
    if not result.ok:
        console.warn(result.stderr.strip() or "Failed to write resolv.conf")
        return False
    return True


def menu(ctx: AppContext) -> None:
    console = ctx.console

    options = [
        "Show current DNS",
        "Set Cloudflare DNS",
        "Reset to automatic DNS",
    ]

    while True:
        choice = select_from_list(console, "DNS options", options)
        if choice is None:
            return

        if is_windows():
            if choice == 0:
                snapshot = _windows_dns_snapshot()
                if not snapshot:
                    console.warn("Failed to read DNS settings.")
                    pause(console)
                    continue
                console.info("Current DNS configuration:")
                for item in snapshot:
                    alias = item.get("InterfaceAlias", "unknown")
                    family = item.get("AddressFamily", "")
                    servers = item.get("ServerAddresses", [])
                    print(f"- {alias} ({family}): {servers}")
                pause(console)
                continue

            if not require_admin(console, ctx.platform, "Changing DNS"):
                pause(console)
                continue

            interfaces = _windows_interfaces()
            if not interfaces:
                console.warn("No interfaces found.")
                pause(console)
                continue
            idx = select_from_list(console, "Select interface", interfaces)
            if idx is None:
                continue
            alias = interfaces[idx]

            if choice == 1:
                if not confirm_sensitive(console, "Apply Cloudflare DNS to this interface?"):
                    continue
                ipv4 = confirm(console, "Configure IPv4?", default=True)
                ipv6 = confirm(console, "Configure IPv6?", default=True)
                ok = _windows_set_dns(alias, ipv4=ipv4, ipv6=ipv6)
                console.success("DNS updated.") if ok else console.warn("DNS update failed.")
                pause(console)
                continue

            if choice == 2:
                if not confirm_sensitive(console, "Reset DNS to automatic (DHCP)?"):
                    continue
                ok = _windows_reset_dns(alias)
                console.success("DNS reset.") if ok else console.warn("DNS reset failed.")
                pause(console)
                continue

        if choice == 0:
            if ctx.platform.has_networkmanager:
                result = run_cmd([
                    "nmcli",
                    "-t",
                    "-f",
                    "NAME,TYPE,IP4.DNS,IP6.DNS",
                    "connection",
                    "show",
                    "--active",
                ])
                console.info(result.stdout.strip() or "No active connections found.")
                pause(console)
                continue
            if ctx.platform.has_resolved:
                result = run_cmd(["resolvectl", "status"])
                console.info(result.stdout.strip() or "No resolvectl output.")
                pause(console)
                continue
            result = run_cmd(["cat", "/etc/resolv.conf"])
            console.info(result.stdout.strip() or "No resolv.conf content.")
            pause(console)
            continue

        if not require_admin(console, ctx.platform, "Changing DNS"):
            pause(console)
            continue

        if choice == 1:
            if not confirm_sensitive(console, "Apply Cloudflare DNS on this system?"):
                continue
            if ctx.platform.has_networkmanager:
                connections = _nmcli_connections(active_only=True) or _nmcli_connections(active_only=False)
                if not connections:
                    console.warn("No NetworkManager connections found.")
                    pause(console)
                    continue
                idx = select_from_list(console, "Select connection", connections)
                if idx is None:
                    continue
                conn = connections[idx]
                ipv4 = confirm(console, "Configure IPv4?", default=True)
                ipv6 = confirm(console, "Configure IPv6?", default=True)
                ok = _nmcli_set_dns(conn, ipv4=ipv4, ipv6=ipv6)
                console.success("DNS updated.") if ok else console.warn("DNS update failed.")
                pause(console)
                continue

            if ctx.platform.has_resolved:
                ok = _update_resolved_conf(console, CLOUDFLARE_V4 + CLOUDFLARE_V6)
                console.success("DNS updated via systemd-resolved.") if ok else console.warn("DNS update failed.")
                pause(console)
                continue

            ok = _write_resolv_conf(console, CLOUDFLARE_V4 + CLOUDFLARE_V6)
            console.success("resolv.conf updated.") if ok else console.warn("resolv.conf update failed.")
            pause(console)
            continue

        if choice == 2:
            if not confirm_sensitive(console, "Reset DNS to automatic settings?"):
                continue
            if ctx.platform.has_networkmanager:
                connections = _nmcli_connections(active_only=True) or _nmcli_connections(active_only=False)
                if not connections:
                    console.warn("No NetworkManager connections found.")
                    pause(console)
                    continue
                idx = select_from_list(console, "Select connection", connections)
                if idx is None:
                    continue
                conn = connections[idx]
                ok = _nmcli_reset_dns(conn)
                console.success("DNS reset.") if ok else console.warn("DNS reset failed.")
                pause(console)
                continue

            console.warn("Automatic DNS reset is not supported for this backend.")
            pause(console)
