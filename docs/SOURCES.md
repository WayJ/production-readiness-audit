# References / 参考来源

These primary references informed packaging/publication. They do not certify this custom rubric or prove any reviewed app is safe. Consulted 2026-11-01.

- MIT license: https://opensource.org/license/mit
- Agent Skills specification: https://agentskills.io/specification
- GitHub Pages publishing source: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Custom Pages workflows: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- Private vulnerability reporting: https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository

Pinned action releases (not a claim that these are the newest releases):

- checkout v6.0.0: https://github.com/actions/checkout/commit/1af3b93b6815bc44a9784bd300feb67ff0d1eeb3
- setup-python v6.0.0: https://github.com/actions/setup-python/commit/e797f83bcb11b83ae66e0230d6156d7c80228e7c
- configure-pages v5.0.0: https://github.com/actions/configure-pages/commit/983d7736d9b0ae728b81ab479565c72886d7745b
- upload-pages-artifact v4.0.0: https://github.com/actions/upload-pages-artifact/commit/7b1f4a764d45c48632c6b24a0339c27f5614fb0b
- deploy-pages v4.0.5: https://github.com/actions/deploy-pages/commit/d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e

SHA pinning reduces mutable-tag risk; it is not proof that an action and all its dependencies are vulnerability-free. Review Dependabot updates and action behavior before changing pins.
