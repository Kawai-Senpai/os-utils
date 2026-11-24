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
- Personal data and device handoff (credential checklist, drive inventory, and OS recovery guidance)

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

## Returning a device

Open **System and Startup → Personal data and device handoff**. Review personal data and sign-ins, then use the storage inventory to identify any additional drives that held local copies. For a company device, follow IT's approved handoff process and preserve work records as required.

- **Windows:** Choose **Master Burn - wipe entire PC (Windows)** for an automatic pre-clean with no folder selection. It previews standard folders in the current Windows profile and default data locations for Chrome, Edge, Brave, Firefox, VS Code, Teams, Slack, Discord, Zoom, WhatsApp (Desktop and Beta), Signal, Telegram, classic Outlook, Thunderbird, Bitwarden, Git and SSH. Close apps and pause sync first. Type **SHRED AND WIPE** to overwrite and delete the files in the preview. The tool reports skipped or failed files. Custom paths, other profiles, and entries held only in Windows Credential Manager are outside this pass. For WhatsApp, use **Linked devices** on your phone to revoke the laptop's session. [WhatsApp unlink instructions](https://faq.whatsapp.com/834124628020911/)
- **Windows Recovery:** After the pre-clean, Master Burn offers to open Recovery. Choose **Rebuild PC → Remove & sanitize → All disks** if prompted for disk scope. Review the target disks, then choose **Sanitize and install** in Windows. If **Remove & sanitize** is unavailable or fails, use the method approved by IT. [Microsoft Cloud rebuild](https://support.microsoft.com/en-us/windows/experience/backup-recovery/cloud-rebuild)
- **Linux:** Use **Show storage devices** to identify drives, then follow **Review Linux drive sanitization steps**. Sanitization runs separately through the approved firmware or offline tool for the specific drive. [NIST media sanitization guidance](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

Master Burn also overwrites files in the current user's standard program folder, `AppData/Local/Programs`. Treat programs listed in the preview as unusable after the pre-clean. The pre-clean skips the running OS Utils files and Python environment so it can still open Recovery. Windows handles the erase of shared installations and Windows files on the selected disks.

Use **Overwrite and delete selected personal files** for an optional pre-clean. Enter explicit files or folders inside your home directory, such as personal documents, a specific browser profile, app data, or a project .env file. Close the affected apps and turn off sync first. The tool previews every file, requires typed confirmation, and overwrites each file with random bytes before deleting it. Folder structure remains. Links, reparse points, and detected mounted storage stop the operation. On Windows, a completed pre-clean offers to open Recovery settings for manual confirmation.

OS Utils also opens Windows Recovery directly and displays read-only inventory and guidance. The native or offline tool handles erasure and reports its result. File overwrites alone can miss SSD remapped blocks, snapshots, and copies. Review cloud data and backups separately and revoke personal sessions from a trusted device.

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
