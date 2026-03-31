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


def _windows_list_rules(console) -> None:
    script = (
        "Get-NetFirewallRule | "
        "Select-Object DisplayName, Enabled, Direction, Action, Profile | "
        "Format-Table -AutoSize"
    )
    _show(console, run_powershell(script))


def _windows_enable_rule(console, enable: bool) -> None:
    name = prompt_text(console, "Rule display name")
    cmd = "Enable-NetFirewallRule" if enable else "Disable-NetFirewallRule"
    _show(console, run_powershell(f"{cmd} -DisplayName \"{name}\""))


def _windows_add_rule(console) -> None:
    name = prompt_text(console, "Rule name")
    direction = "Inbound" if confirm(console, "Inbound rule?", default=True) else "Outbound"
    action = "Allow" if confirm(console, "Allow traffic?", default=True) else "Block"
    protocol = prompt_text(console, "Protocol (TCP/UDP)", default="TCP").upper()
    port = prompt_text(console, "Local port")
    script = (
        "New-NetFirewallRule "
        f"-DisplayName \"{name}\" "
        f"-Direction {direction} "
        f"-Action {action} "
        f"-Protocol {protocol} "
        f"-LocalPort {port}"
    )
    _show(console, run_powershell(script))


def _windows_delete_rule(console) -> None:
    name = prompt_text(console, "Rule display name")
    _show(console, run_powershell(f"Remove-NetFirewallRule -DisplayName \"{name}\""))


def _windows_port_test(console) -> None:
    port = prompt_text(console, "Local port to test")
    script = (
        f"Get-NetTCPConnection -State Listen -LocalPort {port} | "
        "Select-Object -First 10"
    )
    _show(console, run_powershell(script))


def _ufw_available() -> bool:
    return run_cmd(["ufw", "--version"]).ok


def _linux_list_rules(console) -> None:
    _show(console, run_cmd(["ufw", "status", "numbered"]))


def _linux_enable_disable(console, enable: bool) -> None:
    cmd = ["ufw", "enable"] if enable else ["ufw", "disable"]
    _show(console, run_cmd(cmd, use_sudo=True))


def _linux_add_rule(console) -> None:
    direction = "in" if confirm(console, "Inbound rule?", default=True) else "out"
    action = "allow" if confirm(console, "Allow traffic?", default=True) else "deny"
    port = prompt_text(console, "Port")
    protocol = prompt_text(console, "Protocol (tcp/udp/any)", default="tcp").lower()
    if protocol == "any":
        rule = f"{action} {direction} {port}"
    else:
        rule = f"{action} {direction} {port}/{protocol}"
    _show(console, run_cmd(["ufw", *rule.split()], use_sudo=True))


def _linux_delete_rule(console) -> None:
    rule_num = prompt_text(console, "Rule number to delete")
    _show(console, run_cmd(["ufw", "delete", rule_num], use_sudo=True))


def _linux_port_test(console) -> None:
    port = prompt_text(console, "Local port to test")
    result = run_cmd(["bash", "-lc", f"ss -lntup | grep -E ':{port}\\b'"])
    if result.ok and result.stdout.strip():
        console.success("Port is listening:")
        print(result.stdout.strip())
    else:
        console.warn("Port does not appear to be listening.")


def menu(ctx: AppContext) -> None:
    console = ctx.console
    options = [
        "List firewall rules",
        "Enable firewall",
        "Disable firewall",
        "Add rule",
        "Enable rule",
        "Disable rule",
        "Delete rule",
        "Test local port listening",
    ]

    while True:
        choice = select_from_list(console, "Firewall options", options)
        if choice is None:
            return

        if not require_admin(console, ctx.platform, "Firewall management"):
            pause(console)
            continue

        if is_windows():
            if choice == 0:
                _windows_list_rules(console)
            elif choice == 1:
                _show(console, run_powershell("Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True"))
            elif choice == 2:
                _show(console, run_powershell("Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False"))
            elif choice == 3:
                _windows_add_rule(console)
            elif choice == 4:
                _windows_enable_rule(console, enable=True)
            elif choice == 5:
                _windows_enable_rule(console, enable=False)
            elif choice == 6:
                _windows_delete_rule(console)
            elif choice == 7:
                _windows_port_test(console)
            pause(console)
            continue

        if not _ufw_available():
            console.warn("UFW is not available. Install ufw to manage firewall rules.")
            pause(console)
            continue

        if choice == 0:
            _linux_list_rules(console)
        elif choice == 1:
            _linux_enable_disable(console, enable=True)
        elif choice == 2:
            _linux_enable_disable(console, enable=False)
        elif choice == 3:
            _linux_add_rule(console)
        elif choice == 4:
            console.warn("UFW does not enable individual rules; add a rule instead.")
        elif choice == 5:
            console.warn("UFW does not disable individual rules; delete the rule instead.")
        elif choice == 6:
            _linux_delete_rule(console)
        elif choice == 7:
            _linux_port_test(console)
        pause(console)
