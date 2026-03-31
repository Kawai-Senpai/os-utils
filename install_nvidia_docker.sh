#!/usr/bin/env bash
set -euo pipefail

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
else
  echo "Cannot detect OS - /etc/os-release not found."
  exit 1
fi

SUDO=""
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  SUDO="sudo"
fi

INSTALL_DOCKER_ENGINE=false
INSTALL_DOCKER_DESKTOP=false
REMOVE_SNAP_DOCKER=false

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --install-docker-engine)
      INSTALL_DOCKER_ENGINE=true
      ;;
    --install-docker-desktop)
      INSTALL_DOCKER_DESKTOP=true
      ;;
    --remove-snap-docker)
      REMOVE_SNAP_DOCKER=true
      ;;
    --help)
      echo "Usage: $0 [--install-docker-engine | --install-docker-desktop] [--remove-snap-docker]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
  shift
done

if ! command -v docker >/dev/null 2>&1; then
  INSTALL_DOCKER_ENGINE=true
fi

if [[ "$INSTALL_DOCKER_ENGINE" == "true" && "$INSTALL_DOCKER_DESKTOP" == "true" ]]; then
  echo "Choose only one: --install-docker-engine or --install-docker-desktop"
  exit 1
fi

case "${ID:-}" in
  ubuntu|pop|linuxmint)
    $SUDO rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list
    $SUDO apt-get update
    $SUDO apt-get install -y ca-certificates curl gnupg lsb-release ubuntu-drivers-common

    if command -v snap >/dev/null 2>&1 && snap list docker >/dev/null 2>&1; then
      if [[ "$REMOVE_SNAP_DOCKER" == "true" || "$INSTALL_DOCKER_ENGINE" == "true" || "$INSTALL_DOCKER_DESKTOP" == "true" ]]; then
        echo "Removing snap-based Docker."
        $SUDO snap remove docker
      fi
    fi

    if [[ "$INSTALL_DOCKER_ENGINE" == "true" ]]; then
      $SUDO install -m 0755 -d /etc/apt/keyrings
      $SUDO rm -f /etc/apt/keyrings/docker.gpg
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg |
        $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" |
        $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
      $SUDO apt-get update
      $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif [[ "$INSTALL_DOCKER_DESKTOP" == "true" ]]; then
      deb_path="/tmp/docker-desktop-amd64.deb"
      curl -fsSL https://desktop.docker.com/linux/main/amd64/docker-desktop-amd64.deb -o "$deb_path"
      $SUDO apt-get install -y "$deb_path"
    fi

    if ! command -v nvidia-smi >/dev/null 2>&1; then
      echo "Installing NVIDIA driver via ubuntu-drivers. A reboot may be required."
      $SUDO ubuntu-drivers install
    fi

    if ! ldconfig -p 2>/dev/null | grep -q 'libnvidia-ml.so.1'; then
      echo "NVIDIA driver libraries not found. Installing driver via ubuntu-drivers."
      $SUDO ubuntu-drivers install
    fi

    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^nvidia-persistenced\.service'; then
      if [[ ! -e /dev/nvidiactl ]]; then
        echo "NVIDIA device files are missing (/dev/nvidia*). A reboot is likely required before starting nvidia-persistenced."
      else
        if ! $SUDO systemctl start nvidia-persistenced; then
          echo "Failed to start nvidia-persistenced. Check: systemctl status nvidia-persistenced"
        fi
      fi
    fi

    $SUDO install -m 0755 -d /usr/share/keyrings
    $SUDO rm -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
      $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    $SUDO chmod 0644 /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    distro="${ID}${VERSION_ID}"
    list_url="https://nvidia.github.io/libnvidia-container/${distro}/libnvidia-container.list"
    list_tmp="$(mktemp)"

    if ! curl -fsSL "$list_url" -o "$list_tmp"; then
      if [[ "$distro" == "ubuntu24.04" ]]; then
        echo "Repo list not found for ubuntu24.04. Falling back to ubuntu22.04 repo."
        list_url="https://nvidia.github.io/libnvidia-container/ubuntu22.04/libnvidia-container.list"
        if ! curl -fsSL "$list_url" -o "$list_tmp"; then
          echo "Failed to download NVIDIA repo list from: $list_url"
          rm -f "$list_tmp"
          exit 1
        fi
      else
        echo "Failed to download NVIDIA repo list from: $list_url"
        rm -f "$list_tmp"
        exit 1
      fi
    fi

    if ! grep -q '^deb ' "$list_tmp"; then
      echo "Downloaded repo list does not look valid."
      echo "Please verify the URL: $list_url"
      rm -f "$list_tmp"
      exit 1
    fi

    $SUDO rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' "$list_tmp" |
      $SUDO tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    rm -f "$list_tmp"

    $SUDO apt-get update
    $SUDO apt-get install -y nvidia-container-toolkit
    if command -v snap >/dev/null 2>&1 && snap list docker >/dev/null 2>&1; then
      $SUDO nvidia-ctk runtime configure --runtime=docker --config=/var/snap/docker/current/config/daemon.json
      $SUDO snap restart docker
    else
      $SUDO nvidia-ctk runtime configure --runtime=docker
      if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^docker\.service'; then
        $SUDO systemctl restart docker
      else
        echo "Docker service not found. Please restart your Docker daemon manually."
      fi
    fi

    echo "NVIDIA container runtime installed. Reboot if the driver was newly installed."
    ;;
  *)
    echo "Unsupported distro ID: ${ID:-unknown}."
    echo "This script supports ubuntu, pop, and linuxmint only."
    exit 1
    ;;
esac
