try:
    import ultraprint.common as p
except Exception:  # pragma: no cover - optional dependency
    p = None


EMOJI_MAP = {
    "info": "\u2139",
    "success": "\u2705",
    "warn": "\u26a0",
    "error": "\u274c",
    "menu": "\u25b6",
    "network": "\U0001F4F6",
    "system": "\U0001F4BB",
    "packages": "\U0001F4E6",
    "security": "\U0001F512",
    "dev": "\U0001F527",
    "python": "\U0001F40D",
    "git": "\U0001F5C3",
    "tools": "\U0001F9F0",
}


class Console:
    def __init__(self, use_emoji: bool = True) -> None:
        self._p = p
        self.use_emoji = use_emoji

    def _emit(self, method: str, text: str) -> None:
        if self._p and hasattr(self._p, method):
            getattr(self._p, method)(text)
        else:
            print(text)

    def paint(self, text: str, color: str = "lgray") -> None:
        self._emit(color, text)

    def emoji(self, key: str, fallback: str = "") -> str:
        if not self.use_emoji:
            return fallback
        return EMOJI_MAP.get(key, fallback)

    def title(self, text: str) -> None:
        self._emit("bold", text)

    def banner(self, text: str) -> None:
        self.newline()
        self._emit("bold", f"== {text} ==")
        self._emit("dgray", "=" * max(8, len(text) + 8))

    def section(self, text: str) -> None:
        self._emit("blue", f">> {text}")
        self._emit("dgray", "-" * max(8, len(text)))

    def info(self, text: str) -> None:
        prefix = self.emoji("info", "[i]")
        self._emit("cyan", f"{prefix} {text}")

    def success(self, text: str) -> None:
        prefix = self.emoji("success", "[+]")
        self._emit("green", f"{prefix} {text}")

    def warn(self, text: str) -> None:
        prefix = self.emoji("warn", "[!]")
        self._emit("yellow", f"{prefix} {text}")

    def error(self, text: str) -> None:
        prefix = self.emoji("error", "[x]")
        self._emit("red", f"{prefix} {text}")

    def dim(self, text: str) -> None:
        self._emit("dgray", text)

    def kv(self, key: str, value: str) -> None:
        self._emit("lgray", f"{key:<16} {value}")

    def newline(self) -> None:
        if self._p and hasattr(self._p, "n"):
            self._p.n()
        else:
            print("")
