# Contributing / 贡献指南

Discuss concrete changes through issues or pull requests. Never attach real customer code, personal data, credentials or unredacted findings. Vulnerabilities in this toolkit follow SECURITY.md; vulnerabilities found in a reviewed product belong with that product's authorized contact.

Use Python 3.10+ standard library for the core runtime. Keep Windows paths and UTF-8 behavior portable. Prefer small changes with synthetic fixtures and regression tests. Do not turn the diagnostic skill into an unauthorized remediation/deployment tool.

Rule changes: edit only scoring-rubric.json/scoring-policy.json, version the changed semantics, then run `python scripts/review.py sync-rules`. Do not hand edit generated Schema, blank audit or diagnostic-checks.md. Update synthetic examples deliberately; newly added checks stay unknown until the fixture intentionally provides synthetic evidence. Never invent real passes.

Run:

```sh
python scripts/review.py sync-rules --check
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/verify_repo.py
python scripts/package_release.py
```

For UI changes, also run optional Playwright browser checks. Add explicit tests for deductions, duplicate roots, unknowns, blockers, NA and malicious text when relevant. List actual verification and remaining limits in the PR; a workflow configuration is not a completed platform test.

By contributing, you agree that your contribution may be distributed under the repository's MIT license and confirm that you have the rights to submit it. Do not assume customer or employer material is public.
