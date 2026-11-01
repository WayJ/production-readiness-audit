#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build only explicitly allowlisted fictional report examples for public Pages."""
from __future__ import annotations
import shutil
import sys
from common import ROOT, SKILL_REL, deterministic_zip, load_core, skill_files

PUBLIC_EXAMPLES = {
    "audit.demo.json": "report-demo.html",
    "audit.partial.json": "report-partial.html",
}


def main() -> int:
    try:
        audit = load_core()
        site = ROOT / "site"
        site.mkdir(exist_ok=True)
        for source, destination in PUBLIC_EXAMPLES.items():
            data = audit.read_json(ROOT / "examples" / source)
            if data.get("meta", {}).get("is_demo") is not True:
                raise ValueError(f"Public build rejects real audit input: {source}")
            if any(e.get("is_demo") is not True for e in data.get("evidence", [])):
                raise ValueError(f"Public sample must contain only synthetic evidence: {source}")
            audit.save(site / destination, audit.render(data), force=True)
        shutil.copyfile(ROOT / "LICENSE", site / "LICENSE.txt")
        selected = [(p, str(p.relative_to(ROOT / "skills")).replace("\\", "/")) for p in skill_files()]
        deterministic_zip(site / "downloads/production-readiness-audit-skill.zip", selected)
        print("Built public site assets from 2 allowlisted fictional samples; no private reports were read.")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
