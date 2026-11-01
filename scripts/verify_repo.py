#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local consistency checks; not a vulnerability scanner or legal certification."""
from __future__ import annotations
import html.parser
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from common import ROOT, SKILL_REL, load_core, manifest_files


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        for key in ("href", "src"):
            if key in attributes:
                self.links.append(attributes[key])


def check_local_link(source: Path, href: str) -> None:
    if not href or href.startswith(("http:", "https:", "mailto:", "data:", "#")):
        return
    parsed = urlsplit(href)
    if parsed.scheme or href.startswith("//"):
        raise ValueError(f"Unsupported link in {source.name}: {href}")
    dest = (source.parent / unquote(parsed.path)).resolve()
    if not dest.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Link escapes repository: {source.name}: {href}")
    if not dest.exists():
        raise ValueError(f"Missing local link: {source.relative_to(ROOT)} -> {href}")


def main() -> int:
    try:
        audit = load_core()
        audit.sync_rules(check=True)
        files = manifest_files()
        for name in ("audit.demo.json", "audit.partial.json"):
            audit.calculate(audit.read_json(ROOT / "examples" / name))
        audit.calculate(audit.read_json(ROOT / SKILL_REL / "assets/audit.blank.json"))
        if (ROOT / "LICENSE").read_bytes() != (ROOT / SKILL_REL / "LICENSE").read_bytes():
            raise ValueError("Skill and repository LICENSE files differ.")
        if (ROOT / "VERSION").read_text().strip() != audit.VERSION:
            raise ValueError("CLI and repository versions differ.")
        for path in files:
            if path.suffix == ".html" and path.is_relative_to(ROOT / "site"):
                parser = Links()
                parser.feed(path.read_text(encoding="utf-8"))
                for link in parser.links:
                    check_local_link(path, link)
            elif path.suffix == ".md":
                content = path.read_text(encoding="utf-8")
                for target in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)\)", content):
                    check_local_link(path, target)
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            text = workflow.read_text(encoding="utf-8")
            for action in re.findall(r"uses:\s+([^\s]+)", text):
                if not re.fullmatch(r"actions/[A-Za-z0-9_-]+@[0-9a-f]{40}", action):
                    raise ValueError(f"Workflow action is not pinned to an official full SHA: {action}")
            if "pull_request_target" in text:
                raise ValueError("Do not execute untrusted PR code with privileged pull_request_target.")
        sample = audit.render(audit.read_json(ROOT / "examples/audit.demo.json"))
        if "__AUDIT_DATA_JSON__" in sample:
            raise ValueError("Unfilled report template marker.")
        if (ROOT / "site/report-demo.html").read_text(encoding="utf-8").strip() != sample.strip():
            raise ValueError("Public demo is stale. Run python scripts/build_site.py.")
        print(f"Verified {len(files)} manifest files, local document/site links, fixed rubric, public samples and action pins.")
        print("External URLs, evidence truth, remote GitHub settings and platform CI execution are not certified by this check.")
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
