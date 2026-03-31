from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive, require_admin


@dataclass
class PythonInstall:
    label: str
    path: str
    version: str
    manager: str


def _python_version(path: str) -> str:
    result = run_cmd([path, "--version"])
    output = (result.stdout or result.stderr).strip()
    return output.replace("Python ", "") if output else "unknown"


def _classify_python(path: str) -> str:
    lower = path.lower()
    if "pyenv" in lower:
        return "pyenv"
    if ".venv" in lower or "virtualenv" in lower or "venv" in lower:
        return "venv"
    if is_windows() and ("program files" in lower or "appdata" in lower):
        return "python.org"
    if not is_windows() and (lower.startswith("/usr/bin") or lower.startswith("/bin")):
        return "system"
    return "unknown"


def _detect_windows_py() -> List[PythonInstall]:
    installs: List[PythonInstall] = []
    result = run_cmd(["py", "-0p"])
    if not result.ok:
        return installs
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        version = parts[0].lstrip("-")
        path = parts[1]
        installs.append(
            PythonInstall(
                label=f"py {version}",
                path=path,
                version=version,
                manager="py",
            )
        )
    return installs


def _detect_pyenv() -> List[PythonInstall]:
    installs: List[PythonInstall] = []
    result = run_cmd(["pyenv", "versions", "--bare"])
    if not result.ok:
        return installs
    root = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
    for line in result.stdout.splitlines():
        version = line.strip()
        if not version:
            continue
        path = str(Path(root) / "versions" / version / "bin" / "python")
        if Path(path).exists():
            installs.append(
                PythonInstall(
                    label=f"pyenv {version}",
                    path=path,
                    version=version,
                    manager="pyenv",
                )
            )
    return installs


def _detect_path_pythons() -> List[PythonInstall]:
    names = ["python", "python3", "python3.11", "python3.10", "python3.9", "python3.8"]
    installs: List[PythonInstall] = []
    for name in names:
        result = run_cmd(["which", name]) if not is_windows() else run_cmd(["where", name])
        if not result.ok:
            continue
        for path in result.stdout.splitlines():
            path = path.strip()
            if not path:
                continue
            version = _python_version(path)
            installs.append(
                PythonInstall(
                    label=f"{name} ({version})",
                    path=path,
                    version=version,
                    manager=_classify_python(path),
                )
            )
    return installs


def detect_pythons() -> List[PythonInstall]:
    installs: List[PythonInstall] = []
    seen = set()

    for item in _detect_windows_py():
        if item.path not in seen:
            installs.append(item)
            seen.add(item.path)

    for item in _detect_pyenv():
        if item.path not in seen:
            installs.append(item)
            seen.add(item.path)

    for item in _detect_path_pythons():
        if item.path not in seen:
            installs.append(item)
            seen.add(item.path)

    exe = sys.executable
    if exe and exe not in seen:
        installs.append(
            PythonInstall(
                label=f"current ({_python_version(exe)})",
                path=exe,
                version=_python_version(exe),
                manager=_classify_python(exe),
            )
        )

    return installs


def select_python(ctx: AppContext) -> Optional[PythonInstall]:
    installs = detect_pythons()
    if not installs:
        ctx.console.warn("No Python installations detected.")
        return None
    if len(installs) == 1:
        return installs[0]

    labels = [f"{i.label} - {i.path}" for i in installs]
    idx = select_from_list(ctx.console, "Select a Python interpreter", labels)
    if idx is None:
        return None
    return installs[idx]


def _save_preferred(ctx: AppContext, install: PythonInstall) -> None:
    ctx.config.setdefault("python", {})["preferred"] = install.path
    ctx.console.success(f"Preferred Python set to: {install.path}")


def _create_venv(ctx: AppContext) -> None:
    install = select_python(ctx)
    if not install:
        return
    path = prompt_text(ctx.console, "Virtualenv path", default=".venv")
    if not confirm_sensitive(ctx.console, f"Create venv at {path} using {install.path}?"):
        return
    result = run_cmd([install.path, "-m", "venv", path])
    if result.ok:
        ctx.console.success("Virtualenv created.")
    else:
        ctx.console.warn(result.stderr.strip() or "Failed to create venv.")


def _pip_install(ctx: AppContext) -> None:
    install = select_python(ctx)
    if not install:
        return
    package = prompt_text(ctx.console, "Package to install")
    if not confirm_sensitive(ctx.console, f"Install {package} using {install.path}?"):
        return
    result = run_cmd([install.path, "-m", "pip", "install", package])
    if result.ok:
        ctx.console.success("Package installed.")
    else:
        ctx.console.warn(result.stderr.strip() or "pip install failed.")


def _py_supports_uninstall() -> bool:
    result = run_cmd(["py", "--help"])
    output = (result.stdout + result.stderr).lower()
    return "uninstall" in output


def _uninstall_python(ctx: AppContext) -> None:
    console = ctx.console
    installs = detect_pythons()
    if not installs:
        console.warn("No Python installations detected.")
        return
    labels = [f"{i.label} - {i.path}" for i in installs]
    idx = select_from_list(console, "Select Python to uninstall", labels)
    if idx is None:
        return
    target = installs[idx]

    if target.manager == "pyenv":
        if not confirm_sensitive(console, f"Uninstall pyenv {target.version}?"):
            return
        run_cmd(["pyenv", "uninstall", "-f", target.version])
        console.success("pyenv version removed.")
        return

    if target.manager == "venv":
        if not confirm_sensitive(console, f"Delete virtualenv at {target.path}?"):
            return
        if is_windows():
            run_cmd(["cmd", "/c", "rmdir", "/s", "/q", target.path], shell=True)
        else:
            run_cmd(["rm", "-rf", target.path], use_sudo=True)
        console.success("Virtualenv removed.")
        return

    if is_windows():
        methods = ["py uninstall (if available)", "winget uninstall", "Cancel"]
        method = select_from_list(console, "Choose uninstall method", methods, allow_back=False)
        if method is None or method == 2:
            return
        if method == 0:
            if not _py_supports_uninstall():
                console.warn("py uninstall is not available on this system.")
                return
            if not confirm_sensitive(console, f"Run py uninstall --purge {target.version}?"):
                return
            run_cmd(["py", "uninstall", "--purge", target.version])
            console.success("py uninstall command issued.")
            return
        if method == 1:
            if not require_admin(console, ctx.platform, "Uninstalling packages"):
                return
            package_id = prompt_text(console, "winget package id", default="Python.Python.3")
            if not confirm_sensitive(console, f"winget uninstall {package_id}?"):
                return
            run_cmd(["winget", "uninstall", package_id])
            console.success("winget uninstall command issued.")
            return

    if not require_admin(console, ctx.platform, "Uninstalling system Python"):
        return
    pm = ctx.platform.package_manager
    version_hint = target.version.split()[0] if target.version else ""
    default_pkg = f"python{version_hint}" if version_hint else "python3"
    package = prompt_text(console, "Package name", default=default_pkg)
    if not confirm_sensitive(console, f"Remove {package} via {pm}?"):
        return
    if pm == "apt":
        run_cmd(["apt", "remove", "-y", package], use_sudo=True)
    elif pm == "dnf":
        run_cmd(["dnf", "remove", "-y", package], use_sudo=True)
    elif pm == "pacman":
        run_cmd(["pacman", "-Rns", "--noconfirm", package], use_sudo=True)
    console.success("Package removal command issued.")


def menu(ctx: AppContext) -> None:
    options = [
        "List Python installations",
        "Choose preferred Python",
        "Create virtualenv",
        "Install package with pip",
        "Uninstall Python version",
    ]
    while True:
        choice = select_from_list(ctx.console, "Python options", options)
        if choice is None:
            return

        if choice == 0:
            installs = detect_pythons()
            if not installs:
                ctx.console.warn("No Python installations detected.")
                pause(ctx.console)
                continue
            for item in installs:
                print(f"- {item.label} ({item.manager}) -> {item.path}")
            pause(ctx.console)
            continue

        if choice == 1:
            install = select_python(ctx)
            if install:
                _save_preferred(ctx, install)
            pause(ctx.console)
            continue

        if choice == 2:
            _create_venv(ctx)
            pause(ctx.console)
            continue

        if choice == 3:
            _pip_install(ctx)
            pause(ctx.console)
            continue

        if choice == 4:
            _uninstall_python(ctx)
            pause(ctx.console)
