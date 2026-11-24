import os
import stat
import sys
from pathlib import Path
from typing import Callable, Optional

from os_utils.core.console import Console
from os_utils.core.prompt import prompt_text


_CHUNK_SIZE = 1024 * 1024
_WHATSAPP_PACKAGE_DATA_PATHS = tuple(
    f"AppData/Local/Packages/{package}/{folder}"
    for package in ("5319275A.WhatsAppDesktop_cv1g1gvanyjgm", "5319275A.51895FA4EA97F_cv1g1gvanyjgm")
    for folder in ("LocalState", "LocalCache", "RoamingState", "Settings", "TempState")
)
_WINDOWS_PRE_CLEAN_PATHS = (
    "Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
    "AppData/Local/Programs",
    "AppData/Local/Google/Chrome/User Data",
    "AppData/Local/Microsoft/Edge/User Data",
    "AppData/Local/BraveSoftware/Brave-Browser/User Data",
    "AppData/Roaming/Mozilla/Firefox",
    "AppData/Local/Mozilla/Firefox",
    "AppData/Roaming/Code",
    "AppData/Roaming/Code - Insiders",
    ".vscode-shared",
    "AppData/Roaming/Slack",
    "AppData/Roaming/discord",
    "AppData/Roaming/Zoom",
    "AppData/Roaming/WhatsApp",
    *_WHATSAPP_PACKAGE_DATA_PATHS,
    "AppData/Roaming/Signal",
    "AppData/Roaming/Telegram Desktop/tdata",
    "AppData/Roaming/Microsoft/Teams",
    "AppData/Local/Packages/MSTeams_8wekyb3d8bbwe/LocalCache/Microsoft/MSTeams",
    "AppData/Local/Microsoft/Outlook",
    "AppData/Roaming/Microsoft/Outlook",
    "AppData/Roaming/Thunderbird",
    "AppData/Roaming/Bitwarden",
    "AppData/Local/Packages/8bitSolutionsLLC.bitwardendesktop_h4e712dmw3xyy/LocalCache/Roaming/Bitwarden",
    "AppData/Roaming/GitHub CLI",
    ".git-credentials", ".gitconfig", ".ssh", ".config/git", ".config/gh",
    ".env", ".npmrc", ".pypirc",
)
_BROAD_FOLDERS = {
    ("appdata",),
    ("appdata", "local"),
    ("appdata", "locallow"),
    ("appdata", "roaming"),
    (".config",),
    (".local",),
    (".local", "share"),
    (".mozilla",),
    (".var",),
    (".var", "app"),
    ("snap",),
}


def _checked_path(path: Path, home: Path) -> os.stat_result:
    home_info = home.lstat()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"Link or reparse point: {str(current)!r}")
        if current != home and current.is_relative_to(home):
            if info.st_dev != home_info.st_dev or os.path.ismount(current):
                raise ValueError(f"Mounted storage: {str(current)!r}")
    return info


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not info.st_ino:
        raise ValueError("Expected an identifiable regular file with exactly one hard link.")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _target(raw: str, home: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Use an absolute path or a path starting with ~/ and no '..' components.")
    if os.name == "nt" and (
        len(path.drive) != 2
        or not path.drive[0].isalpha()
        or any(":" in part or part.endswith((" ", ".")) for part in path.parts[1:])
        or path.is_reserved()
    ):
        raise ValueError("Use a normal local drive path without alternate streams or reserved names.")
    if path == home or not path.is_relative_to(home):
        raise ValueError("Select a file or folder inside your home directory.")
    parts = tuple(part.casefold() for part in path.relative_to(home).parts)
    if parts in _BROAD_FOLDERS:
        raise ValueError("Select a specific app or browser profile folder inside that directory.")
    if any(part.startswith("onedrive") or part in {"dropbox", "icloud drive", "google drive"} for part in parts):
        raise ValueError("That looks like a synced location. Use the sync provider's controls.")
    return path


def _collect_files(
    target: Path,
    home: Path,
    files: dict[Path, os.stat_result],
    *,
    on_skip: Optional[Callable[[Path, Exception], None]] = None,
    protected_paths: tuple[Path, ...] = (),
) -> None:
    pending = [target]
    while pending:
        path = pending.pop()
        try:
            _target(str(path), home)
            info = _checked_path(path, home)
            if any(path.is_relative_to(protected) for protected in protected_paths):
                raise ValueError("Needed by the running program. Windows Recovery can erase it later.")
            if stat.S_ISDIR(info.st_mode):
                pending.extend(path.iterdir())
            else:
                _file_identity(info)
                files[path] = info
        except (OSError, ValueError) as exc:
            if on_skip is None:
                raise
            if path != target or not isinstance(exc, FileNotFoundError):
                on_skip(path, exc)


def _overwrite_and_delete(path: Path, home: Path, planned: os.stat_result) -> None:
    identity = _file_identity(planned)
    if _file_identity(_checked_path(path, home)) != identity:
        raise ValueError("File changed since preview.")
    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "wb", buffering=0) as handle:
        opened = _file_identity(os.fstat(handle.fileno()))
        # Windows can report different change times for a path and its open handle.
        if opened[:4] != identity[:4]:
            raise ValueError("Opened file differs from the preview.")
        if _file_identity(_checked_path(path, home)) != identity:
            raise ValueError("Path changed before overwrite.")
        remaining = planned.st_size
        while remaining:
            chunk = os.urandom(min(remaining, _CHUNK_SIZE))
            written = handle.write(chunk)
            if not written:
                raise OSError("Overwrite stopped before reaching the original file size.")
            remaining -= written
        os.fsync(handle.fileno())
        overwritten = _file_identity(os.fstat(handle.fileno()))
    current = _file_identity(_checked_path(path, home))
    # Windows may publish updated file times when the writing handle closes.
    same_file = current[:3] == overwritten[:3] if os.name == "nt" else current == overwritten
    if not same_file or current[2] != planned.st_size:
        raise ValueError("File changed during overwrite. Deletion skipped.")
    path.unlink()


def windows_automatic_preclean(console: Console, *, home: Optional[Path] = None) -> Optional[bool]:
    """Return None on cancellation, or whether the pre-clean had no reported failures."""
    home = Path.home() if home is None else home
    files: dict[Path, os.stat_result] = {}
    skipped = 0
    failed = 0
    completed = 0

    def report_skip(path: Path, error: Exception) -> None:
        nonlocal skipped
        skipped += 1
        console.warn(f"Skipped {str(path)!r}. {error}")

    console.section("Automatic pre-clean preview")
    console.info(f"Scanning default locations under {str(home)!r}.")
    try:
        package_path = Path(__file__).resolve().parents[1]
        protected_paths = tuple({
            package_path,
            package_path.with_suffix(".py"),
            Path(sys.executable).resolve(),
            Path(sys.prefix).resolve(),
            Path(sys.base_prefix).resolve(),
        })
        for relative in _WINDOWS_PRE_CLEAN_PATHS:
            found: dict[Path, os.stat_result] = {}
            _collect_files(
                home / relative, home, found, on_skip=report_skip, protected_paths=protected_paths
            )
            if found:
                size = sum(info.st_size for info in found.values())
                console.paint(f"  {relative} ({len(found):,} files, {size:,} bytes)")
                files.update(found)

        if not files:
            console.info("No eligible files found for the automatic pre-clean.")
            return skipped == 0

        console.warn(
            f"This will overwrite and delete {len(files):,} files, including work data in "
            "the listed folders. Programs in the preview may stop working. "
            "SSDs, backups, and cloud copies can retain data."
        )
        if input("Type SHRED AND WIPE to proceed: ") != "SHRED AND WIPE":
            console.info("Canceled. No files changed.")
            return None
    except (EOFError, KeyboardInterrupt):
        console.info("Canceled. No files changed.")
        return None

    console.info("Overwriting and deleting files. This can take several minutes or longer.")
    try:
        for path, planned in files.items():
            try:
                _overwrite_and_delete(path, home, planned)
            except (OSError, ValueError) as exc:
                failed += 1
                console.warn(f"Could not finish {str(path)!r}. {exc}")
            else:
                completed += 1
    except KeyboardInterrupt:
        console.warn(f"Canceled after deleting {completed:,} files. A file may be partially overwritten.")
        return None

    console.info(f"Pre-clean finished. Deleted {completed:,}, failed {failed:,}, skipped {skipped:,}.")
    return failed == 0 and skipped == 0


def preclean(console: Console, *, home: Optional[Path] = None) -> bool:
    home = Path.home() if home is None else home
    console.warn(
        "Close the apps and browsers whose data you selected. Select only personal files "
        "or profiles you are authorized to erase. Disconnect sync before cleaning a synced folder."
    )
    console.info(
        "Add one file or folder at a time. Examples include a personal document, a specific "
        "browser profile, an app's personal data folder, or a project's .env file."
    )
    files: dict[Path, os.stat_result] = {}
    try:
        while True:
            raw = prompt_text(console, "Path (blank to finish)", allow_empty=True)
            if not raw:
                break
            _collect_files(_target(raw, home), home, files)
    except (OSError, ValueError) as exc:
        console.error(f"Preview stopped. No files changed. {exc}")
        return False
    except (EOFError, KeyboardInterrupt):
        console.info("Canceled. No files changed.")
        return False

    if not files:
        console.info("No files selected.")
        return False
    files = dict(sorted(files.items()))
    console.section(f"Preview of {len(files)} files to overwrite and delete")
    for path, info in files.items():
        console.paint(f"  {str(path)!r} ({info.st_size} bytes)")
    console.warn("This is permanent. SSDs, snapshots, backups, and cloud copies can retain data.")
    phrase = f"DELETE {len(files)} FILES"
    try:
        if input(f"Type {phrase} to proceed: ") != phrase:
            console.info("Canceled. No files changed.")
            return False
    except (EOFError, KeyboardInterrupt):
        console.info("Canceled. No files changed.")
        return False

    completed = 0
    path = next(iter(files))
    try:
        # Check the complete preview again before the first write.
        for path, planned in files.items():
            if _file_identity(_checked_path(path, home)) != _file_identity(planned):
                raise ValueError("File changed since preview.")
        for path, planned in files.items():
            _overwrite_and_delete(path, home, planned)
            completed += 1
    except (OSError, ValueError, KeyboardInterrupt) as exc:
        console.error(f"Stopped at {str(path)!r} after deleting {completed} of {len(files)} files. {exc}")
        console.warn("A file may have been partially overwritten. Review the remaining files before retrying.")
        return False

    console.success(f"Overwrote and deleted {completed} files. Folder structure remains.")
    return True
