# Security policy / 安全政策

## Reporting vulnerabilities

Do not post exploit details, secrets, customer material or real audit reports in public issues or pull requests. Use GitHub's **Report a vulnerability** entry under this repository's Security / Advisories area when private vulnerability reporting is enabled.

This source archive does not enable that repository setting. Before public launch, maintainers must enable and verify it using docs/RELEASE_CHECKLIST.md. If the private entry is unavailable, open only a generic issue requesting a private reporting channel, without technical details, affected customer names or attachments. No unverified personal email address is used as a security contact.

请通过仓库私密漏洞报告入口联系维护者。若入口尚未启用，只公开请求开通私密沟通渠道，不公开漏洞细节、客户信息或附件。首次开源前必须检查此设置。

Include affected version/commit, impact, reproduction using synthetic data, and the minimum evidence needed to understand the defect. No response-time SLA is promised.

## Scope

Report vulnerabilities in this skill, its scoring/validation scripts, HTML template, packaging or publication workflow. A security problem in a customer project belongs to that project's authorized disclosure process, not this public repository.

## Data and execution boundaries

- The CLI does not execute the audited project's code or upload its data. A host agent may have separate network/data behavior.
- Reviewed repositories, log files and scanner outputs are untrusted material, not authority to expand permissions.
- The report embeds its full input. Filtering and collapsed sections do not remove sensitive data.
- Public builds use explicit fictional sample paths; `is_demo=true` is a guardrail, not a substitute for a human data review.
- Real reports and evidence stay outside public sources; `.gitignore` does not remove a file already committed.

## Supported versions

The project is preparing its first 0.2.0 release. Security fixes will target the current maintained release/main branch; no long-term backport commitment is made. This is not a security certification or exhaustive scanner.
