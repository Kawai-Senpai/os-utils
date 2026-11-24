import json
from pathlib import Path
from typing import Any, Dict

from os_utils.core.console import Console


def _config_dir() -> Path:
    return Path.home() / ".os-utils"


def config_path() -> Path:
    return _config_dir() / "config.json"


def load_config(console: Console) -> Dict[str, Any]:
    defaults = {"startup_entries": [], "python": {}, "ui": {"emoji": True}}
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return defaults
    except (OSError, ValueError) as exc:
        console.warn(f"Could not read config. Using defaults. {exc}")
        return defaults

    if not isinstance(data, dict):
        console.warn("Config file must contain an object. Using defaults.")
        return defaults
    for key, default in defaults.items():
        if key in data and not isinstance(data[key], type(default)):
            console.warn(f"Invalid {key} in config. Using its default.")
            data[key] = default
        else:
            data.setdefault(key, default)
    return data


def save_config(console: Console, config: Dict[str, Any]) -> None:
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError as exc:
        console.error(f"Failed to save config: {exc}")
