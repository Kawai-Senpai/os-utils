from dataclasses import dataclass
from typing import Dict, Any

from os_utils.core.console import Console
from os_utils.core.platform import PlatformInfo


@dataclass
class AppContext:
    console: Console
    platform: PlatformInfo
    config: Dict[str, Any]
