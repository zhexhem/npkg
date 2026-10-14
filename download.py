"""Download and extract helpers (no git)."""

from __future__ import annotations

import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.error import URLError  # re-exported for callers

from .themes import Logger


def http_download(url: str, dest: Path) -> None:
    """Download a URL to a file with a themed progress bar."""
    t = Logger.theme
    req = urllib.request.Request(url, headers={"User-Agent": "npkg/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        while chunk := resp.read(65536):
            f.write(chunk)
            downloaded += len(chunk)
            if total and t:
                pct = downloaded * 100 // total
                bar = t.progress_bar(pct)
                size = t.muted(f"{downloaded // 1024:>6} KiB")
                sys.stdout.write(f"\r    {bar} {pct:3d}%  {size}")
                sys.stdout.flush()
        if total:
            print()


def sha256_of_tree(path: Path) -> str:
    h = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            h.update(str(file.relative_to(path)).encode())
            h.update(file.read_bytes())
    return h.hexdigest()


def extract_archive(archive: Path, dest: Path) -> Path:
    """Extract .tar.gz or .zip into dest/, stripping one nesting level."""
    tmp = Path(tempfile.mkdtemp(prefix="npkg-"))
    try:
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(archive, "r:gz") as t:
                for member in t.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        raise RuntimeError(f"Unsafe path in archive: {member.name}")
                t.extractall(tmp)

        entries = list(tmp.iterdir())
        root = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp

        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(root), str(dest))
        return dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def github_tarball_url(repo: str, branch: str) -> str:
    """Direct codeload URL — no git, no API auth."""
    return f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"