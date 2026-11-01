#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Repository entry point; the installable skill owns the single implementation."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      "skills/production-readiness-audit/scripts/audit.py"), run_name="__main__")
