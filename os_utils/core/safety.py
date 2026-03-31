from os_utils.core.console import Console
from os_utils.core.platform import PlatformInfo
from os_utils.core.prompt import confirm


def require_admin(console: Console, platform: PlatformInfo, action: str) -> bool:
    if platform.is_admin:
        return True
    console.warn(f"{action} requires admin/root privileges. Please rerun as admin.")
    return False


def confirm_sensitive(console: Console, message: str) -> bool:
    return confirm(console, message, default=False)
