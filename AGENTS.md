# Repository maintenance instructions

This repository contains a diagnostic method and report renderer, not the customer application under review. Keep real inputs, reports, secrets and customer code outside the public manifest and site.

Use Python 3.10+ standard library for core tooling. Preserve Windows support, UTF-8, explicit output paths and overwrite refusal. Never fabricate executed tests or remote publication.

Rule sources are `skills/production-readiness-audit/assets/scoring-rubric.json` and `scoring-policy.json`. Criteria have no weights. Run `python scripts/review.py sync-rules` after source changes and `--check` in validation. Do not hard-code criterion IDs/counts in scoring or UI. Keep root-cause deduplication, unknown states, evidence links, policy fingerprints and explicit blocker rules.

Before release: unit tests, site build, repository verification, optional browser checks, deterministic packaging and fresh-unzip validation. Update actual validation notes. Do not publish real reports through Pages. Editing this toolkit does not authorize modifying a user's reviewed app.
