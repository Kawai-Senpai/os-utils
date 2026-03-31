from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union


@dataclass
class CmdResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    cmd: str


def format_command(cmd: Union[str, Sequence[str]]) -> str:
    if isinstance(cmd, str):
        return cmd
    return " ".join(cmd)


def _is_windows() -> bool:
    return os.name == "nt"


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _is_admin() -> bool:
    if _is_windows():
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0
    return False


def run_cmd(
    cmd: Union[str, Sequence[str]],
    *,
    use_sudo: bool = False,
    shell: bool = False,
    check: bool = False,
    input_text: Optional[str] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> CmdResult:
    actual_cmd: Union[str, List[str]]
    if use_sudo and _is_linux() and not _is_admin():
        if isinstance(cmd, str):
            actual_cmd = f"sudo {cmd}"
        else:
            actual_cmd = ["sudo", *cmd]
    else:
        actual_cmd = list(cmd) if isinstance(cmd, Sequence) and not isinstance(cmd, str) else cmd

    try:
        completed = subprocess.run(
            actual_cmd,
            input=input_text,
            capture_output=True,
            text=True,
            shell=shell,
            check=check,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        return CmdResult(False, 127, "", str(exc), format_command(actual_cmd))
    except subprocess.TimeoutExpired as exc:
        return CmdResult(False, 124, exc.stdout or "", exc.stderr or "", format_command(actual_cmd))

    ok = completed.returncode == 0
    return CmdResult(ok, completed.returncode, completed.stdout, completed.stderr, format_command(actual_cmd))


def run_powershell(script: str, *, check: bool = False) -> CmdResult:
    if not _is_windows():
        return CmdResult(False, 1, "", "PowerShell is only available on Windows.", script)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    return run_cmd(cmd, check=check)


def run_powershell_json(script: str) -> tuple[CmdResult, Optional[Any]]:
    json_script = f"{script} | ConvertTo-Json -Depth 6"
    result = run_powershell(json_script)
    if not result.ok:
        return result, None
    try:
        payload = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        payload = None
    return result, payload
