# OS Utils

Menu-driven system utilities for Windows and Linux. This tool wraps common admin tasks behind clear prompts so you do not have to remember every command.

## What you can do

Network and security
- Wi-Fi password lookup (Windows netsh, Linux NetworkManager)
- Set DNS to Cloudflare or reset to automatic
- SSH install and management (service vs socket on Linux)
- Firewall rules (Windows Defender Firewall, Linux UFW)
- Domain blocking via hosts file

System and startup
- System specs
- Swap file management (Linux only)
- Startup management (Windows startup folder, registry Run, scheduled tasks; Linux autostart and systemd)
- Service control (start/stop/enable/logs)

Software and processes
- Package install, uninstall, and search (winget, apt, dnf, pacman)
- Process inventory, listening ports, timers/scheduled tasks
- Kill process by PID
- NVIDIA drivers, Docker, and NVIDIA container toolkit (Linux)

Developer tools
- Git identity and credential helper setup
- GitHub and GitLab SSH key creation with host aliases
- Python interpreter inventory, venv creation, pip install, uninstall

## Quick start

1) Ensure Python 3.9+ is installed.
2) (Optional) Install colored output:

```bash
pip install ultraprint
```

3) Run the menu:

```bash
python os_utils.py
```

## Safety and privileges

Many actions require admin or root access. The tool will warn and refuse to run when elevation is required. Sensitive actions (DNS changes, Wi-Fi secrets, swap changes, firewall edits, hosts edits, package installs/uninstalls) ask for confirmation first.

## Platform support

Windows
- Requires PowerShell and (optionally) winget for package operations.

Linux
- Designed for systemd-based distros.
- Package managers supported: apt, dnf, pacman.
- Wi-Fi and DNS features use NetworkManager when available.
- Firewall manager uses UFW (if installed).

If a backend is not detected, the tool will explain what is missing.

## Configuration

A config file is stored at:
- ~/.os-utils/config.json

This file keeps:
- Startup entries created by this tool
- Preferred Python path
- UI settings (emoji on/off)

You can edit the file manually if needed.

## Notes and limitations

- Wi-Fi password lookup on Linux requires NetworkManager.
- DNS reset is supported for Windows and NetworkManager. For systemd-resolved or resolv.conf fallback, the tool only applies changes, not automatic rollback.
- Startup removal only tracks entries created by OS Utils; it does not scan every system startup location.
- Python uninstall is cautious by design. System-managed Pythons are removed only via the OS package manager and may impact the OS.
- NVIDIA and Docker helpers are wired for Ubuntu-family (drivers, toolkit) and apt or dnf (Docker).

## Project structure

- os_utils/cli.py: main menu and category routing
- os_utils/core/: shared helpers (console, prompts, command runner, platform detection)
- os_utils/features/: individual features (wifi, dns, swap, startup, etc.)

## Extending the tool

1) Add a new module in os_utils/features with a `menu(ctx)` entry point.
2) Use helpers from os_utils/core:
   - run_cmd, run_powershell
   - require_admin, confirm_sensitive
   - select_from_list, prompt_text
3) Wire the feature into os_utils/cli.py under the appropriate category.

Keep features isolated per file so they remain easy to extend and test.
