from __future__ import annotations

import os
from pathlib import Path

from os_utils.core.context import AppContext
from os_utils.core.platform import is_windows
from os_utils.core.prompt import confirm, pause, prompt_text, select_from_list
from os_utils.core.runner import run_cmd, run_powershell
from os_utils.core.safety import confirm_sensitive


def _git_config(args):
    return run_cmd(["git", *args])


def _set_global_identity(console) -> None:
    name = prompt_text(console, "Git user.name")
    email = prompt_text(console, "Git user.email")
    _git_config(["config", "--global", "user.name", name])
    _git_config(["config", "--global", "user.email", email])
    console.success("Global Git identity updated.")


def _set_local_identity(console) -> None:
    repo = prompt_text(console, "Repository path")
    if not Path(repo).exists():
        console.warn("Path not found.")
        return
    name = prompt_text(console, "Git user.name")
    email = prompt_text(console, "Git user.email")
    _git_config(["-C", repo, "config", "user.name", name])
    _git_config(["-C", repo, "config", "user.email", email])
    console.success("Local Git identity updated.")


def _configure_credentials(console) -> None:
    if is_windows():
        _git_config(["config", "--global", "credential.helper", "manager-core"])
        console.success("Configured Git Credential Manager.")
        return

    options = ["cache (temporary)", "store (plaintext, risky)"]
    idx = select_from_list(console, "Choose credential helper", options)
    if idx is None:
        return
    if idx == 0:
        _git_config(["config", "--global", "credential.helper", "cache"])
        console.success("Credential cache enabled.")
        return
    if idx == 1:
        if not confirm_sensitive(console, "git-credential-store saves passwords in plaintext. Continue?"):
            return
        _git_config(["config", "--global", "credential.helper", "store"])
        console.success("Credential store enabled.")


def _ensure_ssh_agent(console) -> None:
    if is_windows():
        run_powershell("Set-Service -Name ssh-agent -StartupType Automatic")
        run_powershell("Start-Service ssh-agent")
        return
    run_cmd(["ssh-add", "-l"])


def _append_ssh_config(alias: str, host: str, identity_file: str) -> None:
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    config_path = ssh_dir / "config"
    if config_path.exists():
        existing = config_path.read_text(encoding="utf-8")
        if f"Host {alias}" in existing:
            return
    entry = (
        f"Host {alias}\n"
        f"  HostName {host}\n"
        "  User git\n"
        f"  IdentityFile {identity_file}\n"
        "  IdentitiesOnly yes\n\n"
    )
    with config_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def _setup_ssh_account(console, provider: str) -> None:
    email = prompt_text(console, f"{provider} email")
    default_alias = f"{provider}-personal"
    alias = prompt_text(console, "SSH host alias", default=default_alias)
    key_name = prompt_text(console, "SSH key file name", default=f"id_ed25519_{provider}")
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / key_name

    if key_path.exists():
        console.warn("Key already exists. Choose another name or remove it first.")
        return

    run_cmd(["ssh-keygen", "-t", "ed25519", "-C", email, "-f", str(key_path)])
    _ensure_ssh_agent(console)
    run_cmd(["ssh-add", str(key_path)])

    host_name = "github.com" if provider == "github" else "gitlab.com"
    _append_ssh_config(alias, host_name, str(key_path))

    console.success("SSH key created.")
    console.info(f"Public key: {key_path}.pub")
    console.info(f"Use host alias in git remote: {alias}")


def _add_identity_include(console) -> None:
    identity = prompt_text(console, "Identity name")
    name = prompt_text(console, "user.name")
    email = prompt_text(console, "user.email")
    repo_path = prompt_text(console, "Apply to repo path (prefix)")

    config_dir = Path.home() / ".config" / "git" / "identities"
    config_dir.mkdir(parents=True, exist_ok=True)
    identity_file = config_dir / f"{identity}.gitconfig"
    identity_file.write_text(
        f"[user]\n\tname = {name}\n\temail = {email}\n",
        encoding="utf-8",
    )
    include_key = f"includeIf.gitdir:{repo_path}"
    _git_config(["config", "--global", f"{include_key}.path", str(identity_file)])
    console.success("Identity include configured.")


def _switch_identity_for_repo(console) -> None:
    repo = prompt_text(console, "Repository path")
    if not Path(repo).exists():
        console.warn("Path not found.")
        return
    name = prompt_text(console, "user.name")
    email = prompt_text(console, "user.email")
    _git_config(["-C", repo, "config", "user.name", name])
    _git_config(["-C", repo, "config", "user.email", email])
    console.success("Repo identity updated.")


def menu(ctx: AppContext) -> None:
    console = ctx.console
    options = [
        "Set global user.name/email",
        "Set local user.name/email",
        "Configure credential helper",
        "Add GitHub SSH identity",
        "Add GitLab SSH identity",
        "Add includeIf identity",
        "Switch identity for repo",
    ]

    while True:
        choice = select_from_list(console, "Git options", options)
        if choice is None:
            return

        if choice == 0:
            _set_global_identity(console)
        elif choice == 1:
            _set_local_identity(console)
        elif choice == 2:
            _configure_credentials(console)
        elif choice == 3:
            _setup_ssh_account(console, "github")
        elif choice == 4:
            _setup_ssh_account(console, "gitlab")
        elif choice == 5:
            _add_identity_include(console)
        elif choice == 6:
            _switch_identity_for_repo(console)
        pause(console)
