# OS Utils

**System tools for Windows and Linux, in one terminal menu.** Manage networking, services, packages, Git, and Python, or prepare a device for handoff.

[Quick start](#quick-start) · [Tools](#tools) · [Device handoff](#device-handoff) · [Troubleshooting](#troubleshooting) · [Contributing](#contributing)

## Quick start

Download **Code → Download ZIP** from [the repository](https://github.com/Kawai-Senpai/os-utils) and extract the entire folder. If you already use Git, you can clone it instead.

```sh
git clone https://github.com/Kawai-Senpai/os-utils.git
cd os-utils
```

| Platform | Open the menu | If Python is missing or too old |
| --- | --- | --- |
| **Windows** | Double-click **run.bat**. From PowerShell, run **.\run.bat**. | The launcher uses WinGet to install Python 3.13 for your account. Follow any installer prompts. |
| **Linux** | Open a terminal in the extracted folder and run **sh run.sh**. | The launcher uses **apt-get**, **dnf**, or **pacman** to install Python. Enter your sudo password if prompted. |

When **OS Utils** appears, press **Enter**, then type a menu number. Use **0** to go back in a submenu. Choose **Exit** from the main menu when you're done.

<details>
<summary>Run directly or enable colored output</summary>

With Python 3.9 or newer already installed, run **python os_utils.py** on Windows or **python3 os_utils.py** on Linux. For optional colored output, install **ultraprint** into the same Python environment. The menu works with Python alone.

```text
Windows: python -m pip install ultraprint
Linux:   python3 -m pip install ultraprint
```

</details>

## Tools

| Main menu | Available tools |
| --- | --- |
| **Network and Security** | Wi-Fi passwords, Cloudflare DNS, SSH setup, firewall management, and domain blocking through the hosts file. |
| **System and Startup** | System specs, Linux swap, startup entries, services, and personal data and device handoff. |
| **Software and Processes** | Package search, installation and removal, process and listener inventory, process termination, and Linux NVIDIA and Docker helpers. |
| **Developer Tools** | Git identity and credential helper setup, GitHub and GitLab SSH aliases, Python interpreters, virtual environments, and pip packages. |

Start as your usual user. Features that need administrator or root privileges say so. On Windows, PowerShell backs several system tools, and WinGet backs package management. On Linux, package operations support APT, DNF, and Pacman. Service tools are designed for systemd distributions. Wi-Fi lookup needs NetworkManager, firewall management needs UFW, and NVIDIA or Docker support depends on the distribution.

## Device handoff

Open **System and Startup → Personal data and device handoff**. Start with **Review personal data and sign-ins** or **Show storage devices** to check the drives by model, serial number, and capacity.

> [!CAUTION]
> **Master Burn and selected-file shredding permanently erase local data.** On a work device, get IT approval and preserve required work records. Verify your backup and disconnect any drives you want to keep.

### Windows full-device wipe

1. Close browsers and other apps, pause file sync, and plug in the PC.
2. Select **Master Burn - wipe entire PC (Windows)**. Read the automatic preview, especially if browsers, documents, or programs contain a mix of personal and work data.
3. Type **SHRED AND WIPE** to overwrite each eligible file with random bytes before deleting it. Press **Enter** at the confirmation to cancel. The tool reports files it deleted, skipped, or couldn't finish.
4. When prompted, confirm opening Windows Recovery. In Settings, choose **Rebuild PC** under **Rebuild this PC**. In Cloud rebuild, choose **Remove & sanitize**, then **All disks** if prompted and you intend to erase every disk shown. Review the targets, then select **Sanitize and install**.
5. Keep the PC plugged in until Windows finishes. If **Remove & sanitize** is missing, blocked, or fails, use IT's approved drive-sanitization method.

Both shred options report scan activity and show a progress bar during the overwrite. The bar tracks bytes written, or files deleted if all files are empty. The status also reports elapsed time and counts for deleted, failed, and skipped files. Redirected output receives periodic status lines. Windows shows its own progress after you start sanitization in Recovery.

Windows handles drive sanitization and reinstalls the OS. The feature depends on Windows version, hardware, and management policy. [Microsoft Cloud rebuild instructions](https://support.microsoft.com/en-us/windows/experience/backup-recovery/cloud-rebuild)

<details>
<summary>What the automatic pre-clean covers</summary>

The pre-clean searches default locations in the current Windows profile. It skips the running OS Utils files and Python environment so it can reach Recovery.

| Data | Examples |
| --- | --- |
| Personal folders | Desktop, Documents, Downloads, Pictures, Videos, and Music |
| Browser profiles | Chrome, Edge, Brave, and Firefox cookies, local sessions, saved passwords, history, and other profile data |
| App data | VS Code, Teams, Slack, Discord, Zoom, WhatsApp Desktop and Beta, Signal, Telegram, classic Outlook, Thunderbird, and Bitwarden |
| Developer files | Default Git credential files, SSH keys, and supported configuration files for GitHub CLI, npm, and Python package publishing |
| Per-user program files | Eligible files in **AppData/Local/Programs**. Programs in the preview may stop working after the pre-clean. |

Custom paths, other user profiles, credentials held only in Windows Credential Manager, and machine-wide installations are outside the automatic pre-clean. File-level overwrite is best effort and can leave copies in SSD remapped blocks, snapshots, backups, or cloud storage. For the full-device wipe, complete the Windows Recovery step. [NIST media sanitization guidance](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

</details>

Local erasure leaves online account sessions active. Revoke the old device's sessions and rotate any exposed credentials from a trusted device. For WhatsApp, use **Linked devices** on your phone. [WhatsApp unlink instructions](https://faq.whatsapp.com/834124628020911/)

### Selected files and Linux handoff

- **Shred specific files on Windows or Linux:** Choose **Overwrite and delete selected personal files**, enter paths inside your home folder, then press **Enter** on a blank line to finish the list. Confirm the exact phrase shown after the preview. The tool overwrites and deletes eligible files and leaves the folder structure. Close affected apps first and avoid synced folders. Links, mounted locations, and other unsafe entries can stop the preview.
- **Sanitize a Linux drive:** Use **Show storage devices**, then **Review Linux drive sanitization steps**. Use the approved firmware or offline tool for the specific drive, verify its model and serial number, and check the tool's result before handoff. [NIST media sanitization guidance](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

## Troubleshooting

| What you see | What to do |
| --- | --- |
| **Windows launcher can't install Python** | Check the WinGet message. If WinGet is missing or blocked, install Python through your organization's software portal or the [official Python downloads](https://www.python.org/downloads/windows/), then reopen **run.bat**. |
| **Linux launcher can't install Python** | Check the package manager output. Install Python 3.9 or newer through your distribution, then rerun **sh run.sh**. |
| **A feature asks for a missing tool or elevation** | Follow its backend message. Only elevate for features that need it. |
| **Characters look wrong in the terminal** | Set **ui.emoji** to **false** in the configuration file, then reopen the menu. |
| **Files are locked or skipped during Master Burn** | Close the affected apps and review the reported paths. Finish the approved device sanitization before returning the laptop. |

OS Utils stores its configuration in **~/.os-utils/config.json**. It tracks startup entries created by the tool, Python preferences, and UI settings. For DNS changes, automatic reset is available on Windows and NetworkManager. Linux fallback changes through systemd-resolved or resolv.conf may require manual restoration.

## Contributing

- [os_utils.py](os_utils.py) starts the program.
- [os_utils/cli.py](os_utils/cli.py) defines the main menu and category routing.
- [os_utils/core/](os_utils/core/) contains shared prompts, configuration, platform detection, and command execution.
- [os_utils/features/](os_utils/features/) contains the individual tools. Add a **menu(ctx)** entry point and register it under the appropriate category in **cli.py**.

Reuse the shared prompt, privilege, and command helpers. Test destructive workflows with disposable files and mock Recovery launches.
