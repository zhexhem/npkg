"""Console entry point for npkg."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .manager import PluginManager
from .paths import describe, resolve_paths
from .themes import THEMES, Color, Logger, build_theme


def _add_dir_flags(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("directories")
    g.add_argument("--config-dir",
                   help="Where plugins.json / lock.json / runtime.lua live "
                        "(env: NPKG_CONFIG_DIR)")
    g.add_argument("--data-dir",
                   help="Root for downloaded plugin trees (env: NPKG_DATA_DIR)")
    g.add_argument("--plugin-dir",
                   help="Explicit plugin install directory "
                        "(env: NPKG_PLUGIN_DIR) [default: <data-dir>/plugins]")
    g.add_argument("--runtime-file",
                   help="Path to generated runtime.lua "
                        "(env: NPKG_RUNTIME_FILE) [default: <config-dir>/runtime.lua]")


def _cmd_themes(args, no_color: bool) -> int:
    t = Logger.theme
    print(t.banner("npkg themes"))
    print()
    for name, colors in THEMES.items():
        swatch = "".join(
            Color(True).bg(c, "  ") for c in [
                colors["info"], colors["ok"], colors["warn"],
                colors["err"], colors["accent"], colors["title"],
            ] if c
        )
        marker = t.ok("  ← active") if name == t.name else ""
        print(f"  {t.accent(name.ljust(12))} {swatch}{marker}")
    print()
    return 0


def _cmd_paths(args) -> int:
    probe = resolve_paths(
        cli_config_dir=args.config_dir,
        cli_data_dir=args.data_dir,
        cli_plugin_dir=args.plugin_dir,
        cli_runtime_file=args.runtime_file,
    )
    cfg = {}
    if probe.plugins_json.exists():
        try:
            cfg = json.loads(probe.plugins_json.read_text()).get("settings", {})
        except Exception:
            pass
    resolved = resolve_paths(
        cli_config_dir=args.config_dir,
        cli_data_dir=args.data_dir,
        cli_plugin_dir=args.plugin_dir,
        cli_runtime_file=args.runtime_file,
        config_settings=cfg,
    )
    for k, v in resolved.as_dict().items():
        print(f"{k:<14} {v}")
    return 0


def _cmd_init(args) -> int:
    pm = PluginManager(
        cli_config_dir=args.config_dir,
        cli_data_dir=args.data_dir,
        cli_plugin_dir=args.plugin_dir,
        cli_runtime_file=args.runtime_file,
    )
    pm.load_config()
    print(f"Initialized npkg at {pm.paths.config_dir}")
    print(describe(pm.paths))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="npkg")
    parser.add_argument(
        "action",
        choices=["install", "update", "clean", "list", "sync",
                 "themes", "paths", "init"],
    )
    parser.add_argument("--plugin", help="Specific plugin name")
    parser.add_argument("--force", action="store_true", help="Reinstall even if present")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors (also honors NO_COLOR env)")
    parser.add_argument("--theme", help="Override theme for this run")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    _add_dir_flags(parser)
    args = parser.parse_args(argv)

    if args.version:
        print(f"npkg {__version__}")
        return 0

    Logger.bind(build_theme({}, cli_no_color=args.no_color))

    if args.action == "themes":
        return _cmd_themes(args, args.no_color)
    if args.action == "paths":
        return _cmd_paths(args)
    if args.action == "init":
        return _cmd_init(args)

    pm = PluginManager(
        cli_config_dir=args.config_dir,
        cli_data_dir=args.data_dir,
        cli_plugin_dir=args.plugin_dir,
        cli_runtime_file=args.runtime_file,
    )
    pm.connect()
    pm.load_config()

    if args.theme:
        Logger.bind(build_theme({"theme": args.theme}, cli_no_color=args.no_color))

    if args.action == "install":
        pm.install(args.plugin, force=args.force)
    elif args.action == "update":
        pm.update(args.plugin)
    elif args.action == "clean":
        pm.clean()
    elif args.action == "list":
        pm.list_plugins()
    elif args.action == "sync":
        pm.install(force=False)
        pm.update()
        pm.clean()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())