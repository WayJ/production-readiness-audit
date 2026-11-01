# SPDX-License-Identifier: MIT
"""Small shared build utilities; no third-party dependency or network access."""
from __future__ import annotations
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_REL = Path("skills/production-readiness-audit")


def load_core():
    spec = importlib.util.spec_from_file_location("readiness_audit", ROOT / SKILL_REL / "scripts/audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_files() -> list[Path]:
    entries = json.loads((ROOT / "repo-manifest.json").read_text(encoding="utf-8"))["files"]
    if not isinstance(entries, list) or not entries or len(entries) != len(set(entries)):
        raise ValueError("Repository manifest must be a nonempty unique path array.")
    paths = []
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError("Manifest entries must be strings.")
        relative = Path(entry)
        if relative.is_absolute() or ".." in relative.parts or "\\" in entry:
            raise ValueError(f"Unsafe manifest path: {entry}")
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f"Manifest file is missing or unsafe: {entry}")
        paths.append(path)
    return paths


def skill_files() -> list[Path]:
    prefix = (ROOT / SKILL_REL).resolve()
    return [p for p in manifest_files() if p.resolve().is_relative_to(prefix)]


def deterministic_zip(output: Path, files: list[tuple[Path, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError(f"Refusing symlink output: {output}")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(files, key=lambda row: row[1]):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
