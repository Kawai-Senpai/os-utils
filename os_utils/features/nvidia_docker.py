from __future__ import annotations

from os_utils.core.context import AppContext
from os_utils.core.prompt import confirm, pause, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive, require_admin


def _is_ubuntu_family(ctx: AppContext) -> bool:
    distro = (ctx.platform.distro_id or "").lower()
    like = [item.lower() for item in ctx.platform.distro_like]
    return distro in {"ubuntu", "pop", "linuxmint"} or "ubuntu" in like


def _install_nvidia_drivers_ubuntu(ctx: AppContext) -> None:
    run_cmd(["apt", "update"], use_sudo=True)
    run_cmd(["apt", "install", "-y", "ubuntu-drivers-common"], use_sudo=True)
    if confirm(ctx.console, "Use --gpgpu (compute-focused)?", default=False):
        run_cmd(["ubuntu-drivers", "install", "--gpgpu"], use_sudo=True)
    else:
        run_cmd(["ubuntu-drivers", "install"], use_sudo=True)


def _install_docker_ubuntu(ctx: AppContext) -> None:
    console = ctx.console
    remove_cmd = (
        "sudo apt-get remove -y docker.io docker-compose docker-compose-v2 docker-doc "
        "podman-docker containerd runc"
    )
    run_cmd(["bash", "-lc", remove_cmd])
    run_cmd(["bash", "-lc", "sudo apt-get update"], use_sudo=False)
    run_cmd(["bash", "-lc", "sudo apt-get install -y ca-certificates curl gnupg"], use_sudo=False)
    run_cmd(["bash", "-lc", "sudo install -m 0755 -d /etc/apt/keyrings"], use_sudo=False)
    run_cmd(
        [
            "bash",
            "-lc",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
        ]
    )
    run_cmd(["bash", "-lc", "sudo chmod a+r /etc/apt/keyrings/docker.gpg"])
    run_cmd(
        [
            "bash",
            "-lc",
            "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] "
            "https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable\" "
            "| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
        ]
    )
    run_cmd(["bash", "-lc", "sudo apt-get update"])
    run_cmd(
        [
            "bash",
            "-lc",
            "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        ]
    )
    console.success("Docker Engine install commands executed.")


def _install_docker_fedora(ctx: AppContext) -> None:
    run_cmd(
        [
            "bash",
            "-lc",
            "sudo dnf config-manager addrepo --from-repofile https://download.docker.com/linux/fedora/docker-ce.repo",
        ]
    )
    run_cmd(
        [
            "bash",
            "-lc",
            "sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        ]
    )
    run_cmd(["bash", "-lc", "sudo systemctl enable --now docker"])


def _install_nvidia_container_toolkit(ctx: AppContext) -> None:
    if not _is_ubuntu_family(ctx):
        ctx.console.warn("NVIDIA container toolkit installer is only wired for Ubuntu-family.")
        return
    run_cmd(
        [
            "bash",
            "-lc",
            "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
        ]
    )
    run_cmd(
        [
            "bash",
            "-lc",
            "distribution=$(. /etc/os-release && echo ${ID}${VERSION_ID}); "
            "curl -fsSL https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list | "
            "sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | "
            "sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null",
        ]
    )
    run_cmd(["bash", "-lc", "sudo apt-get update"])
    run_cmd(["bash", "-lc", "sudo apt-get install -y nvidia-container-toolkit"])
    run_cmd(["bash", "-lc", "sudo nvidia-ctk runtime configure --runtime=docker"])
    run_cmd(["bash", "-lc", "sudo systemctl restart docker"])


def menu(ctx: AppContext) -> None:
    console = ctx.console
    if not require_admin(console, ctx.platform, "NVIDIA and Docker setup"):
        return

    options = [
        "Install NVIDIA drivers (Ubuntu family)",
        "Install Docker Engine",
        "Install NVIDIA container toolkit",
    ]
    while True:
        choice = select_from_list(console, "NVIDIA and Docker options", options)
        if choice is None:
            return

        if not confirm_sensitive(console, "These actions can modify system packages. Continue?"):
            continue

        if choice == 0:
            if not _is_ubuntu_family(ctx):
                console.warn("NVIDIA driver helper is currently wired for Ubuntu-family only.")
                pause(console)
                continue
            _install_nvidia_drivers_ubuntu(ctx)
            console.success("NVIDIA driver install command issued.")
            pause(console)
            continue

        if choice == 1:
            if ctx.platform.package_manager == "apt":
                _install_docker_ubuntu(ctx)
            elif ctx.platform.package_manager == "dnf":
                _install_docker_fedora(ctx)
            else:
                console.warn("Docker installer supports apt or dnf only for now.")
            pause(console)
            continue

        if choice == 2:
            _install_nvidia_container_toolkit(ctx)
            console.success("NVIDIA container toolkit install command issued.")
            pause(console)
