"""Plugin manager core."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from urllib.error import URLError

from .download import extract_archive, github_tarball_url, http_download, sha256_of_tree
from .paths import Paths, describe, resolve_paths
from .themes import Logger, build_theme


DEFAULT_CONFIG = {
    "settings": {
        "theme": "default",
        "progress_bar": True,
    },
    "plugins": {
        "vim-stylus": {"repo": "wavded/vim-stylus"},
        "nvim-treesitter": {
            "repo": "nvim-treesitter/nvim-treesitter",
            "branch": "master",
            "build": "TSUpdate",
        },
        "plenary.nvim": {"repo": "nvim-lua/plenary.nvim"},
        "telescope.nvim": {
            "repo": "nvim-telescope/telescope.nvim",
            "dependencies": ["plenary.nvim"],
        },
    },
}


class PluginManager:
    def __init__(
        self,
        *,
        cli_config_dir: str | None = None,
        cli_data_dir: str | None = None,
        cli_plugin_dir: str | None = None,
        cli_runtime_file: str | None = None,
    ):
        self.nvim = None
        self.settings: dict = {}
        self.plugins: dict = {}
        self.lock: dict = {}

        self._cli = {
            "cli_config_dir": cli_config_dir,
            "cli_data_dir": cli_data_dir,
            "cli_plugin_dir": cli_plugin_dir,
            "cli_runtime_file": cli_runtime_file,
        }

        # First pass — resolve without config settings so we can find plugins.json
        self.paths: Paths = resolve_paths(**self._cli, config_settings=None).ensure()

    # ------------------------------------------------------------------
    # Neovim connection
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        sock = os.environ.get("NVIM")
        if not sock:
            Logger.log("NVIM env var not set — running in offline mode.", "warn")
            return False
        try:
            import pynvim
            self.nvim = pynvim.attach("socket", path=sock)
            Logger.log(f"Connected to Neovim (channel {self.nvim.channel_id}).")
            return True
        except Exception as e:
            Logger.log(f"Failed to attach to Neovim: {e}", "err")
            return False

    # ------------------------------------------------------------------
    # Config / lock
    # ------------------------------------------------------------------
    def load_config(self) -> None:
        if self.paths.plugins_json.exists():
            data = json.loads(self.paths.plugins_json.read_text())
            if "plugins" in data:
                self.settings = data.get("settings", {})
                self.plugins = data["plugins"]
            else:
                self.settings = {}
                self.plugins = data
        else:
            self.settings = DEFAULT_CONFIG["settings"]
            self.plugins = DEFAULT_CONFIG["plugins"]
            self.save_config()
            Logger.log(f"Created default config at {self.paths.plugins_json}")

        # Second pass — honor settings.* dir overrides
        self.paths = resolve_paths(**self._cli, config_settings=self.settings).ensure()

        if self.paths.lock_file.exists():
            self.lock = json.loads(self.paths.lock_file.read_text())

        Logger.bind(build_theme(self.settings))
        Logger.log(f"Loaded {len(self.plugins)} plugin(s) [theme: {Logger.theme.name}]")
        Logger.log(describe(self.paths), "info")

    def save_config(self) -> None:
        self.paths.plugins_json.write_text(
            json.dumps({"settings": self.settings, "plugins": self.plugins}, indent=2)
        )

    def save_lock(self) -> None:
        self.paths.lock_file.write_text(json.dumps(self.lock, indent=2, sort_keys=True))

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------
    def install(self, name: str | None = None, force: bool = False) -> None:
        targets = [name] if name else list(self.plugins)
        ordered = self._resolve_order(targets)
        for pname in ordered:
            if pname not in self.plugins:
                Logger.log(f"Unknown plugin: {pname}", "err")
                continue
            self._install_one(pname, force=force)
        self.save_lock()
        self._write_runtime_file()

    def _resolve_order(self, names: list[str]) -> list[str]:
        seen, out = set(), []

        def visit(n: str) -> None:
            if n in seen or n not in self.plugins:
                return
            seen.add(n)
            for dep in self.plugins[n].get("dependencies", []):
                visit(dep)
            out.append(n)

        for n in names:
            visit(n)
        return out

    def _install_one(self, name: str, force: bool = False) -> None:
        t = Logger.theme
        info = self.plugins[name]
        repo = info["repo"]
        branch = info.get("branch", "main")
        dest = self.paths.plugin_dir / name

        if dest.exists() and not force:
            Logger.log(
                f"{t.accent(name)}: already installed "
                f"{t.muted('(use --force to reinstall)')}",
                "warn",
            )
            return

        urls = []
        if repo.startswith("http"):
            urls.append(repo)
        else:
            urls.append(github_tarball_url(repo, branch))
            if branch == "main":
                urls.append(github_tarball_url(repo, "master"))

        archive = Path(tempfile.mktemp(suffix=".tar.gz"))
        success = False
        for url in urls:
            try:
                Logger.log(f"{t.accent(name)}: {t.muted(url)}")
                http_download(url, archive)
                success = True
                break
            except (URLError, RuntimeError) as e:
                Logger.log(f"{t.accent(name)}: {e}", "warn")

        if not success:
            Logger.log(f"{t.accent(name)}: all download attempts failed.", "err")
            return

        Logger.log(f"{t.accent(name)}: extracting…")
        extract_archive(archive, dest)
        archive.unlink(missing_ok=True)

        checksum = sha256_of_tree(dest)
        self.lock[name] = {"repo": repo, "branch": branch, "sha256": checksum}
        Logger.log(
            f"{t.accent(name)}: installed {t.muted('(' + checksum[:12] + '…)')}",
            "ok",
        )

        if "build" in info and self.nvim:
            self._run_build(name, info["build"])

    # ------------------------------------------------------------------
    # Update / clean / list
    # ------------------------------------------------------------------
    def update(self, name: str | None = None) -> None:
        t = Logger.theme
        targets = [name] if name else list(self.plugins)
        for pname in targets:
            if pname not in self.plugins:
                Logger.log(f"Unknown plugin: {pname}", "err")
                continue
            old = self.lock.get(pname, {}).get("sha256")
            self._install_one(pname, force=True)
            new = self.lock.get(pname, {}).get("sha256")
            if old and new and old == new:
                Logger.log(f"{t.accent(pname)}: already up-to-date.", "warn")
        self._write_runtime_file()

    def clean(self) -> None:
        t = Logger.theme
        configured = set(self.plugins.keys())
        installed = {p.name for p in self.paths.plugin_dir.iterdir() if p.is_dir()}
        orphans = installed - configured
        if not orphans:
            Logger.log("Nothing to clean.")
            return
        for orphan in orphans:
            shutil.rmtree(self.paths.plugin_dir / orphan)
            self.lock.pop(orphan, None)
            Logger.log(f"Removed orphan: {t.accent(orphan)}", "ok")
        self.save_lock()
        self._write_runtime_file()

    def list_plugins(self) -> None:
        t = Logger.theme
        print()
        print(t.banner("npkg"))
        print()

        def pad(s: str, w: int) -> str:
            return s + " " * max(0, w - len(s))

        print(t.heading(pad("Plugin", 24)) + t.heading(pad("Repo", 42)) + t.heading("Status"))
        print(t.hr())
        print(t.muted(describe(self.paths)))
        print()

        for name, info in self.plugins.items():
            installed = (self.paths.plugin_dir / name).exists()
            badge = t.badge("installed", "ok") if installed else t.badge("missing", "err")
            print(t.accent(pad(name, 24)) + pad(info["repo"], 42) + badge)

        configured = set(self.plugins.keys())
        installed_dirs = {p.name for p in self.paths.plugin_dir.iterdir() if p.is_dir()}
        orphans = installed_dirs - configured
        if orphans:
            print()
            print(t.warn(f"{len(orphans)} orphan(s) on disk (run `npkg clean`):"))
            for o in sorted(orphans):
                print("  " + t.badge(o, "warn"))
        print()

    # ------------------------------------------------------------------
    # Build / runtime file
    # ------------------------------------------------------------------
    def _run_build(self, name: str, cmd: str) -> None:
        t = Logger.theme
        self.nvim.command(f"set rtp^={self.paths.plugin_dir / name}")
        try:
            Logger.log(f"{t.accent(name)}: running build `{cmd}`…")
            self.nvim.command(cmd)
            Logger.log(f"{t.accent(name)}: build complete.", "ok")
        except Exception as e:
            Logger.log(f"{t.accent(name)}: build failed: {e}", "err")

    def _write_runtime_file(self) -> None:
        lines = [
            "-- AUTO-GENERATED by npkg. Do not edit by hand.",
            f"-- config_dir = {self.paths.config_dir}",
            f"-- plugin_dir = {self.paths.plugin_dir}",
            f'vim.g.npkg_config_dir = "{self.paths.config_dir}"',
            f'vim.g.npkg_plugin_dir = "{self.paths.plugin_dir}"',
            f'vim.g.npkg_theme = "{self.settings.get("theme", "default")}"',
            'vim.g.npkg_theme_colors = vim.fn.json_decode([==['
            + json.dumps(Logger.theme.colors)
            + ']==])',
            "",
        ]
        for name in self.plugins:
            path = self.paths.plugin_dir / name
            if path.exists():
                lines.append(f'vim.opt.rtp:prepend("{path}")')
        self.paths.runtime_file.write_text("\n".join(lines) + "\n")
        Logger.log(f"Wrote {self.paths.runtime_file}")