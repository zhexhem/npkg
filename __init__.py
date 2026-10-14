"""npkg — Neovim Plugin Manager (git-free, tarball-based, themeable)."""

__version__ = "0.2.0"
__author__ = "You"
__license__ = "MIT"

from .manager import PluginManager
from .paths import Paths, resolve_paths, describe
from .themes import THEMES, Color, Logger, Theme, build_theme

__all__ = [
    "__version__",
    "PluginManager",
    "Paths",
    "resolve_paths",
    "describe",
    "THEMES",
    "Color",
    "Logger",
    "Theme",
    "build_theme",
]