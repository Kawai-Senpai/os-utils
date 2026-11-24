#!/bin/sh
set -eu

cd -- "$(dirname -- "$0")"
if [ ! -f os_utils.py ]; then
    printf '%s\n' 'os_utils.py is missing. Extract the entire OS Utils archive and rerun run.sh.' >&2
    exit 1
fi
printf '%s\n' 'Starting OS Utils...'

find_python() {
    for python in python3 python; do
        if command -v "$python" >/dev/null 2>&1 &&
            "$python" -I -c 'import sys; sys.exit(not ((3, 9) <= sys.version_info[:2]))' >/dev/null 2>&1; then
            return 0
        fi
    done
    return 1
}

as_admin() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        printf '%s\n' 'Installing Python requires an administrator or sudo.' >&2
        return 1
    fi
}

install_python() {
    if command -v apt-get >/dev/null 2>&1; then
        as_admin apt-get update && as_admin apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        as_admin dnf install -y python3
    elif command -v pacman >/dev/null 2>&1; then
        as_admin pacman -S --needed python
    else
        printf '%s\n' 'Install Python 3.9 or newer using your distribution package manager.' >&2
        return 1
    fi
}

if ! find_python; then
    printf '%s\n' 'Python 3.9 or newer was not found. Setting it up with the system package manager...'
    if ! install_python; then
        printf '%s\n' 'Python setup did not finish. Review the error above and rerun run.sh.' >&2
        exit 1
    fi
    if ! find_python; then
        printf '%s\n' 'No compatible Python was found. Install Python 3.9 or newer, then rerun run.sh.' >&2
        exit 1
    fi
fi

exec "$python" -B os_utils.py
