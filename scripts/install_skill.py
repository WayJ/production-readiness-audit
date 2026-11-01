#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Copy the self-contained skill into an explicitly chosen skills directory."""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
from common import ROOT, SKILL_REL, skill_files


def install(target: Path) -> Path:
    source = ROOT / SKILL_REL
    destination = target.expanduser().resolve() / source.name
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists; choose a new directory: {destination}")
    if destination.is_relative_to(source.resolve()) or source.resolve().is_relative_to(destination):
        raise ValueError("Installation destination must be separate from the source skill.")
    selected = skill_files()
    if not selected:
        raise ValueError("No skill files were selected by the manifest.")
    # Only known distribution files are copied, never local audit outputs or caches.
    destination.mkdir(parents=True, exist_ok=False)
    for path in selected:
        out = destination / path.relative_to(source)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True, help="The skills parent directory chosen for your host.")
    args = parser.parse_args()
    try:
        destination = install(args.target)
        print(f"Copied skill to: {destination}")
        print("Configure your agent host to load this directory. No host settings were changed.")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
