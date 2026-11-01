# v0.2.0 验收记录 / Validation

## 实际执行环境

2026-11-01，当前Linux容器，Python 3.13.5，Chromium 144.0.7559.96。此记录对应本次完整项目包；不代表已在客户项目执行审查。

## 已执行

- 86项标准库自动测试全部通过。实际输出见[unit-tests.txt](validation/unit-tests.txt)。覆盖扣分计算、根因去重、同指标多问题、多指标同根因、维度封底、阻断、未知、NA、规则扩展、版本与哈希、Schema生成、输入转义、CSP、CLI、独立Skill安装、中文路径与覆盖保护。
- 生成的JSON Schema经本地jsonschema Draft202012Validator检查；完整示例、部分示例和空白草稿均通过结构校验。该库只用于此次附加验证，不是核心依赖。
- Playwright/Chromium浏览器检查通过：[browser-tests.txt](validation/browser-tests.txt)。包含9维/4问题显示、59分、搜索、筛选、展开、打印事件前后恢复、锚点、恶意文本不执行、中文及英文页面390/768/1440像素宽度检查、Windows与Unix命令切换、暂评上限展示。
- sync-rules --check通过；样例、文档和本地链接、公开资源白名单、工作流SHA固定规则通过verify_repo校验。
- 完整示例实际基础分91、加权扣分9、阻断2项、最终59。部分示例为25/27指标已完成、2项未知，最终分为空、暂评上限59。空白草稿未评估。
- 完整工程与独立Skill均按白名单打包；还需结合本文件末尾的实际解压复验记录。

## 未验证或受限

Windows/macOS实机、Python3.10实机、GitHub远程CI、Pages部署、Release发布和特定Agent宿主自动发现未执行。仓库的跨平台CI配置不等于这些平台已经通过。

浏览器测试通过set_content加载完整自包含HTML，验证DOM/脚本与CSP，不验证真实线上URL或下载链路。本容器浏览器管理策略阻止file://导航，因此未以该方式实测双击打开。实际打印对话框和PDF文件输出未验证，仅测试beforeprint/afterprint事件及筛选恢复。

未审查真实客户应用，不能声称发现其缺陷或证明其生产就绪。规则、自动测试与HTML转义不能替代证据真实性和业务判断。

## 复现命令

```sh
python scripts/review.py sync-rules --check
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/verify_repo.py
python scripts/package_release.py
# 可选：安装Playwright/Chromium后指定实际浏览器路径
python tests/browser_smoke.py --browser /path/to/chromium
```

核心工具不需要联网或第三方Python库。测试记录仅表示实际执行的检查，不是安全认证。

## 解压复验结果

已将完整工程ZIP解压到新的目录，再次执行86项自动测试，全部通过；sync-rules --check与verify_repo再次通过；成功生成完整示例HTML；成功用中文项目名初始化草稿并生成未评估报告（score=None，不显示正式100分）。独立Skill安装到带空格目录后的独立渲染也包含在已通过的分发测试中。

最终交付包在更新本记录后重新生成；SHA-256校验文件与交付ZIP一同提供。未执行GitHub上传。
