#!/usr/bin/env python3
"""
npkg : Neovim Plugin Manager — setup script.

Metadata lives in pyproject.toml. This file adds:
  * a post-install hint when pynvim isn't importable
  * a fallback metadata block for old setuptools (<61) / missing pyproject.toml
"""

from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

HERE = Path(__file__).parent.resolve()
README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""

_PYNVIM_HINT = (
    "\n"
    "──────────────────────────────────────────────────────────────────\n"
    " npkg installed.\n\n"
    " Heads-up: `pynvim` was not importable at install time. npkg still\n"
    " works in offline mode, but in-session `:Npkg*` commands need it:\n\n"
    "     pip install pynvim\n\n"
    " You'll also want the Neovim Python provider set up once:\n\n"
    "     :python3 import pynvim\n\n"
    " See: https://github.com/neovim/pynvim\n"
    "──────────────────────────────────────────────────────────────────\n"
)


def _pynvim_available() -> bool:
    try:
        import pynvim  # noqa: F401
        return True
    except ImportError:
        return False


class PostInstall(_install):
    def run(self):
        super().run()
        if not _pynvim_available():
            print(_PYNVIM_HINT, file=sys.stderr)


class PostDevelop(_develop):
    def run(self):
        super().run()
        if not _pynvim_available():
            print(_PYNVIM_HINT, file=sys.stderr)


if not (HERE / "pyproject.toml").exists():
    setup(
        name="npkg",
        version="0.2.0",
        description="Neovim Plugin Manager — git-free, tarball-based, themeable",
        long_description=README,
        long_description_content_type="text/markdown",
        author="You",
        author_email="you@example.com",
        url="https://github.com/you/npkg",
        license="MIT",
        python_requires=">=3.9",
        packages=["npkg"],
        include_package_data=True,
        install_requires=["pynvim>=0.5.0"],
        extras_require={"dev": ["pytest>=7", "pytest-cov", "ruff", "black", "mypy"]},
        entry_points={"console_scripts": ["npkg = npkg.cli:main"]},
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Software Development :: Build Tools",
            "Topic :: Text Editors",
        ],
        cmdclass={"install": PostInstall, "develop": PostDevelop},
        zip_safe=False,
    )
else:
    setup(cmdclass={"install": PostInstall, "develop": PostDevelop})