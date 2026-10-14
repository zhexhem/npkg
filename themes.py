"""Themes and color engine for npkg CLI output."""

from __future__ import annotations

import os
import sys


# ---------------------------------------------------------------------------
# Built-in themes — every theme maps semantic roles to hex colors.
# Add your own by copying a block and giving it a new name.
# ---------------------------------------------------------------------------
THEMES: dict[str, dict[str, str]] = {
    "default": {
        "info": "#89b4fa", "ok": "#a6e3a1", "warn": "#f9e2af", "err": "#f38ba8",
        "muted": "#6c7086", "accent": "#cba6f7", "title": "#f5c2e7",
        "heading": "#89dceb", "bar_fg": "#1e1e2e", "bar_bg": "#89b4fa",
    },
    "dracula": {
        "info": "#8be9fd", "ok": "#50fa7b", "warn": "#f1fa8c", "err": "#ff5555",
        "muted": "#6272a4", "accent": "#bd93f9", "title": "#ff79c6",
        "heading": "#8be9fd", "bar_fg": "#282a36", "bar_bg": "#bd93f9",
    },
    "gruvbox": {
        "info": "#83a598", "ok": "#b8bb26", "warn": "#fabd2f", "err": "#fb4934",
        "muted": "#928374", "accent": "#d3869b", "title": "#fe8019",
        "heading": "#8ec07c", "bar_fg": "#282828", "bar_bg": "#b8bb26",
    },
    "nord": {
        "info": "#88c0d0", "ok": "#a3be8c", "warn": "#ebcb8b", "err": "#bf616a",
        "muted": "#4c566a", "accent": "#b48ead", "title": "#81a1c1",
        "heading": "#8fbcbb", "bar_fg": "#2e3440", "bar_bg": "#88c0d0",
    },
    "tokyo": {
        "info": "#7aa2f7", "ok": "#9ece6a", "warn": "#e0af68", "err": "#f7768e",
        "muted": "#565f89", "accent": "#bb9af7", "title": "#ff007c",
        "heading": "#7dcfff", "bar_fg": "#1a1b26", "bar_bg": "#7aa2f7",
    },
    "solarized": {
        "info": "#268bd2", "ok": "#859900", "warn": "#b58900", "err": "#dc322f",
        "muted": "#586e75", "accent": "#6c71c4", "title": "#d33682",
        "heading": "#2aa198", "bar_fg": "#002b36", "bar_bg": "#268bd2",
    },
    "mono": {role: "" for role in (
        "info", "ok", "warn", "err", "muted", "accent",
        "title", "heading", "bar_fg", "bar_bg",
    )},
}


class Color:
    """Truecolor ANSI helper. Auto-degrades if the terminal can't do color."""

    RESET = "\033[0m"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @staticmethod
    def supports_color() -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        if not sys.stdout.isatty():
            return False
        if os.environ.get("TERM", "") in ("", "dumb"):
            return False
        return True

    def _hex_to_rgb(self, h: str):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def fg(self, hex_color: str, text: str) -> str:
        if not self.enabled or not hex_color:
            return text
        r, g, b = self._hex_to_rgb(hex_color)
        return f"\033[38;2;{r};{g};{b}m{text}{self.RESET}"

    def bg(self, hex_color: str, text: str) -> str:
        if not self.enabled or not hex_color:
            return text
        r, g, b = self._hex_to_rgb(hex_color)
        return f"\033[48;2;{r};{g};{b}m{text}{self.RESET}"

    def bold(self, text: str) -> str:
        return f"\033[1m{text}{self.RESET}" if self.enabled else text

    def dim(self, text: str) -> str:
        return f"\033[2m{text}{self.RESET}" if self.enabled else text


class Theme:
    """Wraps a theme dict with convenience paint methods."""

    def __init__(self, name: str, colors: dict[str, str], enabled: bool = True):
        self.name = name
        self.colors = colors
        self.c = Color(enabled)

    def __getitem__(self, role: str) -> str:
        return self.colors.get(role, "")

    def info(self, t):    return self.c.fg(self["info"], t)
    def ok(self, t):      return self.c.fg(self["ok"], t)
    def warn(self, t):    return self.c.fg(self["warn"], t)
    def err(self, t):     return self.c.fg(self["err"], t)
    def muted(self, t):   return self.c.fg(self["muted"], t)
    def accent(self, t):  return self.c.fg(self["accent"], t)
    def title(self, t):   return self.c.bold(self.c.fg(self["title"], t))
    def heading(self, t): return self.c.bold(self.c.fg(self["heading"], t))

    def badge(self, label: str, role: str) -> str:
        glyphs = {"ok": "✓", "err": "✗", "warn": "●", "info": "•"}
        g = glyphs.get(role, "·")
        return self.c.fg(self[role], f"{g} {label}")

    def progress_bar(self, pct: int, width: int = 24) -> str:
        filled = int(width * pct / 100)
        empty = width - filled
        bar = self.c.bg(self["bar_bg"], " " * filled) + self.c.fg(self["muted"], "░" * empty)
        return f"[{bar}]"

    def hr(self, width: int = 78) -> str:
        return self.c.fg(self["muted"], "─" * width)

    def banner(self, text: str) -> str:
        line = "─" * (len(text) + 4)
        top = self.c.fg(self["accent"], f"╭{line}╮")
        mid = self.c.fg(self["accent"], "│ ") + self.title(text) + self.c.fg(self["accent"], " │")
        bot = self.c.fg(self["accent"], f"╰{line}╯")
        return f"{top}\n{mid}\n{bot}"


def build_theme(settings: dict, cli_no_color: bool = False) -> Theme:
    """Resolve theme name + user overrides + color capability into a Theme."""
    name = settings.get("theme", "default")
    base = THEMES.get(name, THEMES["default"]).copy()
    base.update(settings.get("theme_colors", {}))

    enabled = not cli_no_color and Color.supports_color()
    if name == "mono":
        enabled = False
    return Theme(name, base, enabled)


class Logger:
    """Global logger with theme binding."""

    theme: Theme = None  # type: ignore

    @classmethod
    def bind(cls, theme: Theme) -> None:
        cls.theme = theme

    @classmethod
    def log(cls, msg: str, level: str = "info") -> None:
        t = cls.theme
        icons = {"info": "•", "ok": "✓", "warn": "!", "err": "✗"}
        painter = getattr(t, level, t.info)
        print(f"{painter(icons[level])} {msg}", flush=True)