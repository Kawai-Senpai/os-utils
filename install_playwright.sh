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

BROWSERS="all"
VENV_PATH=""
PYTHON_PATH=""
USE_SYSTEM_PIP=true
SKIP_DEPS=false
INSTALL_NAKED_WEB=true

usage() {
  cat <<'EOF'
Usage: ./install_playwright.sh [options]

Options:
  --browsers <all|chromium|firefox|webkit>  Browsers to install (default: all)
  --venv <path>                             Create/use a venv at path and install there
  --python <path>                           Use a specific python executable
  --system-pip                              Use system pip (default)
  --skip-deps                               Skip OS dependency installation
  --skip-naked-web                          Skip installing naked-web[automation]
  --help                                    Show this help
EOF
}

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --browsers)
      BROWSERS="${2:-}"
      shift 2
      ;;
    --venv)
      VENV_PATH="${2:-}"
      USE_SYSTEM_PIP=false
      shift 2
      ;;
    --python)
      PYTHON_PATH="${2:-}"
      shift 2
      ;;
    --system-pip)
      USE_SYSTEM_PIP=true
      shift 1
      ;;
    --skip-deps)
      SKIP_DEPS=true
      shift 1
      ;;
    --skip-naked-web)
      INSTALL_NAKED_WEB=false
      shift 1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

case "$BROWSERS" in
  all|chromium|firefox|webkit)
    ;;
  *)
    echo "Invalid --browsers value: $BROWSERS"
    usage
    exit 1
    ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Please install Python 3."
  exit 1
fi

if [[ "$SKIP_DEPS" == "false" ]]; then
  case "${ID:-}" in
    ubuntu|pop|linuxmint|debian)
      ASOUND_PKG="libasound2"
      if apt-cache policy libasound2 2>/dev/null | grep -q 'Candidate: (none)'; then
        ASOUND_PKG="libasound2t64"
      fi
      $SUDO apt-get update
      $SUDO apt-get install -y \
        ca-certificates \
        curl \
        wget \
        gnupg \
        python3-venv \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libpangocairo-1.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        "$ASOUND_PKG" \
        libdrm2 \
        libxshmfence1 \
        libxfixes3 \
        libxrender1 \
        libxtst6 \
        libxkbcommon0 \
        libgtk-3-0
      ;;
    *)
      echo "Unsupported distro ID: ${ID:-unknown}."
      echo "Install system dependencies manually or re-run with --skip-deps."
      ;;
  esac
fi

if [[ -n "$PYTHON_PATH" ]]; then
  PYTHON_BIN="$PYTHON_PATH"
else
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    PYTHON_BIN="python3"
  fi
fi

PIP_BIN="$PYTHON_BIN -m pip"

if [[ -n "$VENV_PATH" ]]; then
  $PYTHON_BIN -m venv "$VENV_PATH"
  # shellcheck disable=SC1091
  source "$VENV_PATH/bin/activate"
  PYTHON_BIN="python"
  PIP_BIN="python -m pip"
fi

$PIP_BIN install --upgrade pip
$PIP_BIN install --upgrade playwright
if [[ "$INSTALL_NAKED_WEB" == "true" ]]; then
  $PIP_BIN install --upgrade "naked-web[automation]"
fi

if [[ "$BROWSERS" == "all" ]]; then
  if [[ "$SKIP_DEPS" == "true" ]]; then
    $PYTHON_BIN -m playwright install
  else
    $PYTHON_BIN -m playwright install --with-deps
  fi
else
  if [[ "$SKIP_DEPS" == "true" ]]; then
    $PYTHON_BIN -m playwright install "$BROWSERS"
  else
    $PYTHON_BIN -m playwright install --with-deps "$BROWSERS"
  fi
fi

echo "Playwright installation complete."
