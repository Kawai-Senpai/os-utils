from os_utils.core.console import Console
from os_utils.core.config import load_config, save_config
from os_utils.core.context import AppContext
from os_utils.core.platform import detect_platform
from os_utils.core.prompt import select_from_list, pause
from os_utils.features import (
    dns,
    domain_blocker,
    firewall,
    git,
    nvidia_docker,
    packages,
    privacy,
    processes,
    python_tools,
    services,
    specs,
    ssh,
    startup,
    swap,
    wifi,
)


def main() -> None:
    console = Console()
    config = load_config(console)
    console = Console(use_emoji=config.get("ui", {}).get("emoji", True))
    platform = detect_platform(console)
    ctx = AppContext(console=console, platform=platform, config=config)

    def run_category(title: str, items: list[tuple[str, callable]]) -> None:
        while True:
            choice = select_from_list(console, title, [item[0] for item in items])
            if choice is None:
                return
            items[choice][1](ctx)

    network_items = [
        (f"{console.emoji('network', '[N]')} Wi-Fi passwords", wifi.menu),
        (f"{console.emoji('network', '[N]')} DNS to Cloudflare", dns.menu),
        (f"{console.emoji('security', '[S]')} SSH setup", ssh.menu),
        (f"{console.emoji('security', '[FW]')} Firewall manager", firewall.menu),
        (f"{console.emoji('security', '[BL]')} Domain blocking", domain_blocker.menu),
    ]

    system_items = [
        (f"{console.emoji('system', '[SYS]')} System specs", specs.menu),
        (f"{console.emoji('system', '[SYS]')} Swap space (Linux)", swap.menu),
        (f"{console.emoji('system', '[SYS]')} Startup management", startup.menu),
        (f"{console.emoji('system', '[SYS]')} Service control", services.menu),
        (f"{console.emoji('security', '[S]')} Personal data and device handoff", privacy.menu),
    ]

    software_items = [
        (f"{console.emoji('packages', '[PKG]')} Packages", packages.menu),
        (f"{console.emoji('tools', '[PROC]')} Processes and inventory", processes.menu),
        (f"{console.emoji('tools', '[GPU]')} NVIDIA and Docker", nvidia_docker.menu),
    ]

    dev_items = [
        (f"{console.emoji('git', '[GIT]')} Git setup", git.menu),
        (f"{console.emoji('python', '[PY]')} Python management", python_tools.menu),
    ]

    menu_items = [
        (f"{console.emoji('network', '[N]')} Network and Security", lambda: run_category("Network and Security", network_items)),
        (f"{console.emoji('system', '[SYS]')} System and Startup", lambda: run_category("System and Startup", system_items)),
        (f"{console.emoji('packages', '[PKG]')} Software and Processes", lambda: run_category("Software and Processes", software_items)),
        (f"{console.emoji('dev', '[DEV]')} Developer Tools", lambda: run_category("Developer Tools", dev_items)),
        ("Exit", None),
    ]

    console.banner("OS Utils")
    console.kv("OS", platform.os_label)
    if platform.distro_id:
        console.kv("Distro", f"{platform.distro_id} {platform.version_id or ''}".strip())
    console.kv("Admin", "yes" if platform.is_admin else "no")
    console.dim("Tip: use [0] to go back in menus.")
    pause(console, "Press Enter to open the menu...")

    while True:
        console.banner("Main Menu")
        options = [item[0] for item in menu_items]
        choice = select_from_list(console, "Choose an option", options, allow_back=False)
        if choice is None:
            break
        _, handler = menu_items[choice]
        if handler is None:
            console.info("Goodbye.")
            break
        try:
            handler()
        except KeyboardInterrupt:
            console.warn("Action canceled.")
        except Exception as exc:  # pragma: no cover - defensive
            console.error(f"Unexpected error: {exc}")

    save_config(console, config)


if __name__ == "__main__":
    main()
