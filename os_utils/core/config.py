import json
from pathlib import Path
from typing import Any, Dict

from os_utils.core.console import Console


def _config_dir() -> Path:
    return Path.home() / ".os-utils"


def config_path() -> Path:
    return _config_dir() / "config.json"


def load_config(console: Console) -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {"startup_entries": [], "python": {}, "ui": {"emoji": True}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "startup_entries" not in data:
            data["startup_entries"] = []
        if "python" not in data:
            data["python"] = {}
        if "ui" not in data:
            data["ui"] = {"emoji": True}
        return data
    except json.JSONDecodeError:
        console.warn("Config file is invalid. Using defaults.")
        return {"startup_entries": [], "python": {}, "ui": {"emoji": True}}


def save_config(console: Console, config: Dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError as exc:
        console.error(f"Failed to save config: {exc}")
