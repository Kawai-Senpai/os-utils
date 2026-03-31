from __future__ import annotations

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import pause, select_from_list
from os_utils.core.runner import run_cmd, run_powershell


def menu(ctx: AppContext) -> None:
    console = ctx.console

    options = ["Show system specs"]
    while True:
        choice = select_from_list(console, "System specs", options)
        if choice is None:
            return

        if is_windows():
            script = (
                "Get-ComputerInfo | Select-Object CsName, OsName, OsVersion, OsArchitecture, "
                "WindowsVersion, CsTotalPhysicalMemory, CsNumberOfLogicalProcessors | Format-List; "
                "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List"
            )
            result = run_powershell(script)
            console.info(result.stdout.strip() or result.stderr.strip())
            pause(console)
            continue

        commands = [
            "uname -a",
            "lsb_release -a 2>/dev/null || cat /etc/os-release",
            "lscpu",
            "free -h",
            "lsblk",
            "df -h",
        ]
        result = run_cmd(["bash", "-lc", "\n".join(commands)])
        console.info(result.stdout.strip() or result.stderr.strip())
        pause(console)
