from __future__ import annotations

import os
from pathlib import Path
from typing import List

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive, require_admin


def _hosts_path() -> Path:
    if is_windows():
        system_root = os.environ.get("SystemRoot", "C:\\Windows")
        return Path(system_root) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def _normalize_domain(raw: str) -> str:
    cleaned = raw.strip().lower()
    for prefix in ("http://", "https://"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    cleaned = cleaned.split("/")[0]
    return cleaned


def _read_hosts() -> List[str]:
    path = _hosts_path()
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_hosts(lines: List[str]) -> bool:
    path = _hosts_path()
    content = "\n".join(lines) + "\n"
    if is_windows():
        try:
            path.write_text(content, encoding="utf-8")
            return True
        except OSError:
            return False
    tmp = Path("/tmp/os-utils-hosts")
    tmp.write_text(content, encoding="utf-8")
    return run_cmd(["cp", str(tmp), str(path)], use_sudo=True).ok


def _blocked_domains(lines: List[str]) -> List[str]:
    domains: List[str] = []
    for line in lines:
        if "# os-utils" in line:
            parts = line.split()
            if len(parts) >= 2:
                domains.append(parts[1])
    return sorted(set(domains))


def _block_domain(ctx: AppContext) -> None:
    console = ctx.console
    raw = prompt_text(console, "Domain or URL to block")
    domain = _normalize_domain(raw)
    lines = _read_hosts()
    existing = _blocked_domains(lines)
    if domain in existing:
        console.warn("Domain already blocked.")
        return
    lines.append(f"0.0.0.0 {domain} # os-utils")
    if _write_hosts(lines):
        ctx.config.setdefault("blocked_domains", []).append(domain)
        console.success(f"Blocked {domain} via hosts file.")
    else:
        console.warn("Failed to update hosts file. Run as admin/root.")


def _unblock_domain(ctx: AppContext) -> None:
    console = ctx.console
    lines = _read_hosts()
    blocked = _blocked_domains(lines)
    if not blocked:
        console.warn("No blocked domains found.")
        return
    idx = select_from_list(console, "Select domain to unblock", blocked)
    if idx is None:
        return
    target = blocked[idx]
    new_lines = [line for line in lines if target not in line or "# os-utils" not in line]
    if _write_hosts(new_lines):
        ctx.config.setdefault("blocked_domains", [])
        ctx.config["blocked_domains"] = [d for d in ctx.config["blocked_domains"] if d != target]
        console.success(f"Unblocked {target}.")
    else:
        console.warn("Failed to update hosts file. Run as admin/root.")


def menu(ctx: AppContext) -> None:
    console = ctx.console
    options = ["List blocked domains", "Block domain", "Unblock domain"]

    while True:
        choice = select_from_list(console, "Domain blocking", options)
        if choice is None:
            return

        if not require_admin(console, ctx.platform, "Hosts file changes"):
            pause(console)
            continue

        lines = _read_hosts()
        if choice == 0:
            blocked = _blocked_domains(lines)
            if not blocked:
                console.warn("No blocked domains found.")
            else:
                console.info("Blocked domains:")
                for domain in blocked:
                    print(f"- {domain}")
            pause(console)
            continue

        if choice == 1:
            if not confirm_sensitive(console, "Block a domain using the hosts file?"):
                continue
            _block_domain(ctx)
            pause(console)
            continue

        if choice == 2:
            if not confirm_sensitive(console, "Unblock a domain?"):
                continue
            _unblock_domain(ctx)
            pause(console)
