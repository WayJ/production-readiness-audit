# SPDX-License-Identifier: MIT
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import deterministic_zip, manifest_files
from install_skill import install


class DistributionTests(unittest.TestCase):
    def test_manifest_excludes_private_roots_and_caches(self):
        for file in manifest_files():
            rel = file.relative_to(ROOT)
            self.assertNotIn(rel.parts[0], {"reports", "review-data", "private", "dist", ".git"})
            self.assertNotIn("__pycache__", rel.parts)
            self.assertNotEqual(file.suffix, ".pyc")

    def test_zip_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp)/"a.zip", Path(temp)/"b.zip"
            selected = [(ROOT / "LICENSE", "production-readiness-audit/LICENSE")]
            deterministic_zip(a, selected)
            deterministic_zip(b, selected)
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
            with zipfile.ZipFile(a) as archive:
                self.assertEqual(archive.namelist(), ["production-readiness-audit/LICENSE"])

    def test_install_refuses_existing_target(self):
        with tempfile.TemporaryDirectory() as temp:
            first = install(Path(temp))
            self.assertTrue((first/"SKILL.md").is_file())
            with self.assertRaisesRegex(ValueError, "already exists"):
                install(Path(temp))

    def test_installed_skill_is_self_contained(self):
        with tempfile.TemporaryDirectory(prefix="installed skill ") as temp:
            installed = install(Path(temp)/"host skills")
            source = ROOT / "examples/audit.demo.json"
            output = Path(temp)/"standalone report.html"
            process = subprocess.run([sys.executable, str(installed/"scripts/audit.py"), "render", "--input",
                                      str(source), "--output", str(output)], cwd=temp,
                                     capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("report-data", output.read_text(encoding="utf-8"))
            self.assertTrue((installed/"LICENSE").is_file())

    def test_public_builder_allowlist_exact(self):
        from build_site import PUBLIC_EXAMPLES
        self.assertEqual(set(PUBLIC_EXAMPLES), {"audit.demo.json", "audit.partial.json"})
        for filename in PUBLIC_EXAMPLES:
            data = json.loads((ROOT/"examples"/filename).read_text(encoding="utf-8"))
            self.assertIs(data["meta"]["is_demo"], True)
            self.assertTrue(all(e["is_demo"] for e in data["evidence"]))

    def test_init_cli_with_unicode_path(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/"中文目录"/"审查.json"
            process = subprocess.run([sys.executable, str(ROOT/"scripts/review.py"), "init", "--project", "客户示例",
                                      "--output", str(output)], capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["project"], "客户示例")
            self.assertFalse(data["baseline_ready"])


if __name__ == "__main__":
    unittest.main()
