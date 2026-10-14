"""
Path resolution for npkg.

Priority (highest → lowest):
    1. CLI flags
    2. Environment variables (NPKG_*)
    3. Config file settings
    4. XDG base dirs
    5. Hardcoded ~/.config / ~/.local/share fallbacks
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def _expand(p) -> Path | None:
    if p is None or p == "":
        return None
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()


@dataclass
class Paths:
    config_dir: Path
    data_dir: Path
    plugin_dir: Path
    runtime_file: Path

    lock_file: Path = field(init=False)
    plugins_json: Path = field(init=False)

    def __post_init__(self):
        self.lock_file = self.config_dir / "lock.json"
        self.plugins_json = self.config_dir / "plugins.json"

    def ensure(self) -> "Paths":
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        return self

    def as_dict(self) -> dict[str, str]:
        return {
            "config_dir": str(self.config_dir),
            "data_dir": str(self.data_dir),
            "plugin_dir": str(self.plugin_dir),
            "runtime_file": str(self.runtime_file),
            "lock_file": str(self.lock_file),
            "plugins_json": str(self.plugins_json),
        }


def resolve_paths(
    *,
    cli_config_dir: str | None = None,
    cli_data_dir: str | None = None,
    cli_plugin_dir: str | None = None,
    cli_runtime_file: str | None = None,
    config_settings: dict | None = None,
) -> Paths:
    cfg = config_settings or {}

    config_dir = (
        _expand(cli_config_dir)
        or _expand(os.environ.get("NPKG_CONFIG_DIR"))
        or _expand(cfg.get("config_dir"))
        or (_xdg_config_home() / "nvim" / "npkg")
    )

    data_dir = (
        _expand(cli_data_dir)
        or _expand(os.environ.get("NPKG_DATA_DIR"))
        or _expand(cfg.get("data_dir"))
        or (_xdg_data_home() / "nvim" / "npkg")
    )

    plugin_dir = (
        _expand(cli_plugin_dir)
        or _expand(os.environ.get("NPKG_PLUGIN_DIR"))
        or _expand(cfg.get("plugin_dir"))
        or (data_dir / "plugins")
    )

    runtime_file = (
        _expand(cli_runtime_file)
        or _expand(os.environ.get("NPKG_RUNTIME_FILE"))
        or _expand(cfg.get("runtime_file"))
        or (config_dir / "runtime.lua")
    )

    return Paths(config_dir, data_dir, plugin_dir, runtime_file)


def describe(p: Paths) -> str:
    return (
        f"config={p.config_dir}  "
        f"data={p.data_dir}  "
        f"plugins={p.plugin_dir}  "
        f"runtime={p.runtime_file}"
    )