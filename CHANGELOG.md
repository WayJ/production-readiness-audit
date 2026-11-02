# Changelog

## Unreleased

- Show rubric indicator names in report titles: pending-verification cards and the check table now read "A1 · 核心业务链真实完成" instead of repeating the bare id "A1 · A1".
- Lead both READMEs and both landing pages with installation and invocation: the skill install command and copyable agent prompts now appear before everything else.

## 0.2.0 — 2026-11-01

- Replace criterion point allocations with fixed dimension weights and finding-based deductions (3/10/20/40 by default).
- Separate the versioned rubric and scoring policy. Add `sync-rules` and drift checks for the generated schema, unreviewed starter and criterion reference.
- Support multiple findings per criterion and multiple criteria per root cause without double charging. Reject duplicate root-cause records.
- Separate severity, critical review and explicit evidence-based blocker rules.
- Show unreviewed/partial states honestly; no default 100 for unchecked dimensions. Unknowns have no point allocations.
- Embed exact rule snapshots and hashes; allow frozen rule files through CLI flags.
- Update fixed HTML, bilingual docs and site, synthetic examples, browser checks and distribution tests.
- Preserve MIT license, safe-output behavior, private-report exclusion, self-contained skill and gated Pages configuration.

## 0.1.0 — 2026-11-01

Initial repository preparation with a weighted-criterion rubric, standalone skill, fixed HTML report, bilingual site, license and GitHub workflow configurations. Superseded by the explicit deduction model; old report semantics are not silently rewritten.
