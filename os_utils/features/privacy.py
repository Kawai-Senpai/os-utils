import os

from os_utils.core.console import Console
from os_utils.core.context import AppContext
from os_utils.core.platform import is_linux, is_windows
from os_utils.core.prompt import pause, select_from_list
from os_utils.core.runner import run_cmd
from os_utils.core.safety import confirm_sensitive
from os_utils.features.shred import preclean, windows_automatic_preclean


def _handoff_checklist(console: Console) -> None:
    console.section("Personal data to review before handoff")
    for item in (
        "Arrange the handoff with IT. Preserve required work data and ask IT to remove your local profile if the installed OS must be kept.",
        "Check all local drives and user profiles, including personal documents, downloads, recycle bin or trash, and synced folders.",
        "Review browser profiles, cookies and sessions, saved passwords, autofill data, and extensions.",
        "Review app profiles and cached mail, chat, cloud storage, password managers, saved sign-ins, and system credential stores.",
        "Review development folders and local VMs or containers for .env files, environment variables, SSH keys, API tokens, CLI logins, and package registry credentials.",
        "Sign out of personal browsers and apps, unlink device sync, and revoke the laptop's active sessions from a trusted device. Rotate reusable secrets that may have been exposed.",
        "Check cloud copies and backups separately. Erasing a local drive leaves server-side copies and active server-side sessions outside the erase scope.",
    ):
        console.info(item)


def _show_drives(console: Console, windows: bool) -> None:
    if windows:
        command = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "$ErrorActionPreference = 'Stop'; "
            "Get-Disk | Format-Table Number,FriendlyName,SerialNumber,BusType,Size,IsBoot,IsSystem | "
            "Out-String -Width 200",
        ]
    else:
        command = [
            "lsblk", "--paths", "--output",
            "NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINTS",
        ]
    result = run_cmd(command, timeout=15)
    if result.ok and result.stdout.strip():
        console.paint(result.stdout.strip())
    elif result.returncode == 124:
        console.error("Storage inventory timed out.")
    else:
        detail = (result.stderr or result.stdout).strip()
        console.error(f"Could not list storage devices. {detail}".rstrip())
    console.dim("Before sanitizing, verify each intended drive by model, serial number, and capacity.")


def _open_windows_recovery(console: Console) -> None:
    console.info("Opening Windows Recovery settings. Windows reports progress after you start sanitization there.")
    try:
        os.startfile("ms-settings:recovery")
    except OSError as exc:
        console.error(f"Could not open Recovery settings. {exc}")
        console.info("Open Settings > Recovery manually. On Windows 10, look under Update & Security.")


def _master_burn(console: Console) -> None:
    console.section("Master Burn - full Windows PC wipe")
    console.warn(
        "A full wipe permanently erases local files, browser data, app data, and accounts "
        "on every disk you confirm in Windows. On a work PC, get IT approval first."
    )
    console.info("Verify your backup, disconnect drives you want to keep, and plug the PC into power.")
    console.info("Close browsers and apps, and pause sync before continuing.")
    outcome = windows_automatic_preclean(console)
    if outcome is None:
        return
    if not outcome:
        console.warn("Some local data remains. Review the pre-clean results before opening Recovery.")
    console.info("In Recovery, choose Rebuild PC under Rebuild this PC if available.")
    console.info(
        "Choose Remove & sanitize, then All disks if prompted. Verify the disk scope "
        "and select Sanitize and install. Windows handles the erase and reinstall."
    )
    console.info("If Remove & sanitize is unavailable or fails, use IT's approved sanitization process.")
    console.info("Microsoft instructions https://support.microsoft.com/en-us/windows/experience/backup-recovery/cloud-rebuild")
    if confirm_sensitive(console, "Open Windows Recovery for a full PC wipe?"):
        _open_windows_recovery(console)


def _linux_sanitization(console: Console) -> None:
    console.section("Offline drive sanitization")
    console.warn("On a work device, use the sanitization or reimage procedure approved by IT.")
    console.info("Verify your backup and disconnect any drives that should be kept.")
    console.info("Use the approved firmware tool or boot from trusted service media before erasing a system drive.")
    console.info("Match each target's model, serial number, and capacity against the drive inventory.")
    console.info(
        "Use the sanitization method supported by that specific drive and approved for the data. "
        "File overwrites, formatting, and reinstalling alone can leave recoverable data."
    )
    console.info("Check and record the sanitization result for every target drive before returning the device.")
    console.info("NIST guidance https://csrc.nist.gov/pubs/sp/800/88/r2/final")


def _preclean_and_offer_recovery(console: Console, windows: bool) -> None:
    if preclean(console) and windows:
        console.info("For a full PC wipe, use Cloud rebuild > Remove & sanitize in Windows Recovery.")
        if confirm_sensitive(console, "Open Windows Recovery settings now?"):
            _open_windows_recovery(console)


def menu(ctx: AppContext) -> None:
    console = ctx.console
    windows = is_windows()
    linux = is_linux()
    actions = [("Review personal data and sign-ins", _handoff_checklist)]
    if windows or linux:
        actions.append(("Show storage devices", lambda output: _show_drives(output, windows)))
    if windows:
        actions.append(("Master Burn - wipe entire PC (Windows)", _master_burn))
    if linux:
        actions.append(("Review Linux drive sanitization steps", _linux_sanitization))
    if windows or linux:
        actions.append((
            "Overwrite and delete selected personal files",
            lambda output: _preclean_and_offer_recovery(output, windows),
        ))

    while True:
        choice = select_from_list(console, "Personal data and device handoff", [label for label, _ in actions])
        if choice is None:
            return
        actions[choice][1](console)
        pause(console)
