# GitHub 首次发布清单 / First-publication checklist

此包完成文件准备，不表示仓库已经创建、代码已经上传、Pages 已启用、跨平台 CI 已执行或 v0.2.0 已发布。
This package prepares files; it does not create a repository, upload code, enable Pages, execute remote CI or publish a release.

## 1. 仓库信息 / Repository metadata

- Owner / 账号：`WayJ`。
- Name / 名称：`production-readiness-audit`。
- Visibility / 可见性：Public（按本次开源准备）；先确认所有内容有权公开。
- Default branch：`main`。
- Description：

```text
Evidence-based production readiness reviews for AI-built apps. Check bugs, security, architecture and concurrency, then generate scored offline HTML reports.
```

中文说明：为 AI 开发的软件做上线前技术诊断，覆盖漏洞、Bug、架构、代码组织和并发，输出有证据的九维评分 HTML 报告。

Suggested topics：

```text
agent-skills, code-review, production-readiness, vibe-coding, ai-coding, security-review, software-quality, concurrency, architecture, html-report, python
```

预计 Pages 地址（**实际部署成功前不要声称已上线**）：
`https://wayj.github.io/production-readiness-audit/`

仓库改名或迁到组织时，全文更新 `WayJ/production-readiness-audit` 链接，包括两个官网、README引用和 Issue 配置；工作流无需硬编码账号。

## 2. 上传前 / Before uploading

- [ ] 确认版权主体；当前 LICENSE 为 `Copyright (c) 2026 WayJ and contributors`。企业所有的材料需有相应授权。
- [ ] 确认接受 MIT 开放授权；不要擅自给第三方资产重授权。
- [ ] 检查所有 examples 与 site 仅含虚构数据；特别注意 HTML 内嵌 JSON。
- [ ] 确认没有客户代码、密钥、真实审查数据或旧仓库历史。
- [ ] 执行下列验证与打包，检查输出。

```text
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/verify_repo.py
python scripts/package_release.py
```

`repo-manifest.json` 是发布包的显式文件白名单。新增公共文件需人工更新；打包不会把 reports/、review-data/、缓存或任意新文件自动装进去。Git 提交本身仍需检查。

## 3. 创建空仓库并推送 / Create an empty repository and push

在 GitHub 创建 Public 空仓库。**不要再自动生成 README、License 或 .gitignore**，以免与此包冲突。解压后进入包含 README 的根目录执行（PowerShell/macOS/Linux 通用）：

```text
git init
git branch -M main
git add .
git status --short
git diff --cached --stat
```

先检查暂存文件，确认没有真实数据。然后：

```text
git commit -m "feat: initial evidence-based production readiness audit"
git remote add origin https://github.com/WayJ/production-readiness-audit.git
git push -u origin main
```

若远程已有提交，先读取与比较，不要使用强制推送覆盖。GitHub 凭据由本机正常登录流程提供，不把 token 写在命令、仓库或聊天里。

## 4. 启用 GitHub Pages / Enable the site

1. Repository Settings → Pages → Build and deployment → Source = **GitHub Actions**。
2. Settings → Secrets and variables → Actions → Variables，添加普通仓库变量 `ENABLE_PAGES`，值为 `true`。它不是密钥；用于显式开启公开部署。
3. Actions → Deploy Pages → Run workflow，选择 main；也可以在开启后再推送 main 触发。
4. 查看实际 deployment 输出地址，测试首页、英文页、完整报告、待验证报告和 Skill 下载。
5. 将实际 Pages URL 填入仓库 About → Website；不要在首次部署前把它当有效链接宣传。

只有 `site/` 会被上传，不使用仓库根目录。不要把真实审查结果放入 site。Pages 的公开边界独立于代码仓库可见性，私有仓库也不能被当作页面访问控制。

可在 github-pages environment 限制只允许 main 部署。静态官网不需要域名或云服务器，本包未添加 CNAME。

## 5. 安全与协作设置 / Security and collaboration

- [ ] 启用并验证 Private vulnerability reporting；SECURITY.md 不能替代此开关。
- [ ] 确认 Issues 可用，模板显示正常。
- [ ] 观察 CI 的六个系统/版本组合实际结果；未运行不能标为已通过。
- [ ] 按团队权限条件配置 main 保护/ruleset；至少避免未经检查直接合并。
- [ ] 确认 Dependabot 能提出 action pin 更新；不要自动接受未审阅的供应链变更。
- [ ] 不创建虚假 Star、下载数、用户评价、构建成功标记或性能承诺。

## 6. 首个 Release / First release

本包的 `VERSION` 为0.2.0。CI通过、README和网站检查完成后再创建 `v0.2.0` tag/release。用 docs/RELEASE_NOTES.md 作为说明草稿，上传 dist 里的两个ZIP和SHA256SUMS。

`package_release.py` 只在本地产生文件，不创建 tag，也不上传 Release。当前未附自动发布工作流，避免推送或打标签意外公开内容。

官方依据见 [SOURCES.md](SOURCES.md)。
