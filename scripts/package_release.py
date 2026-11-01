#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create deterministic source/skill ZIPs from an explicit manifest, plus SHA-256 sums."""
from __future__ import annotations
import argparse
import hashlib
import sys
from pathlib import Path
from common import ROOT, deterministic_zip, manifest_files, skill_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        import re
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
            raise ValueError("VERSION must contain a safe semantic version.")
        out = args.output.resolve()
        out.mkdir(parents=True, exist_ok=True)
        source = out / f"production-readiness-audit-{version}.zip"
        skill = out / f"production-readiness-audit-skill-{version}.zip"
        selected = manifest_files()
        if any(p.resolve() in {source.resolve(), skill.resolve()} for p in selected):
            raise ValueError("Release output cannot overwrite a source-manifest file.")
        deterministic_zip(source, [(p, "production-readiness-audit/" + p.relative_to(ROOT).as_posix())
                                   for p in selected])
        deterministic_zip(skill, [(p, p.relative_to(ROOT / "skills").as_posix()) for p in skill_files()])
        sums = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in (source, skill))
        (out / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
        print(f"Created {source.name}, {skill.name}, SHA256SUMS in {out}")
        print("Nothing was uploaded, tagged or published.")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
