# 快速开始 / Quick start

Python 3.10+。核心工具无第三方Python依赖；在解压后的仓库根目录运行。Windows把下面的 `python` 换成 `py -3`。

## 体验虚构报告

```sh
python scripts/review.py render --input examples/audit.demo.json --output reports/demo.html
python scripts/review.py render --input examples/audit.partial.json --output reports/partial.html
```

用现代浏览器打开HTML。文件可离线显示、筛选、展开和打印。示例不是项目审查；不需要运行客户应用。

## 创建真实审查

```sh
python scripts/review.py init --project "客户项目" --snapshot "真实提交或包哈希" --output review-data/audit.json
```

这是全unknown草稿。按Skill建立基线，使用授权隔离环境检查。确认问题需要证据、触发条件、根因、影响范围、最小建议、复验标准和严重度依据。未知与确认问题严格分开。

```sh
python scripts/review.py validate --input review-data/audit.json
python scripts/review.py score --input review-data/audit.json
python scripts/review.py render --input review-data/audit.json --output reports/review.html --json-output reports/review.scored.json
```

validate只能证明结构和关联满足契约，不能证明证据真实或审查充分。默认拒绝覆盖；优先使用新文件名，确需覆盖才使用 `--force`。不允许输出覆盖输入。

## 独立Skill包

解压独立包后保留整个production-readiness-audit目录。在该目录运行：

```sh
python scripts/audit.py init --project "项目名称" --output private-audit.json
python scripts/audit.py render --input private-audit.json --output private-review.html
```

或在完整工程中执行 `python scripts/install_skill.py --target /宿主支持的skills目录`。Windows目录带空格时加引号。自动发现流程由宿主决定，不声称已验证所有Agent。

## 指标同步和本地官网

```sh
python scripts/review.py sync-rules
python scripts/review.py sync-rules --check
python scripts/build_site.py
python -m http.server 8000 --directory site --bind 127.0.0.1
```

最后一条启动本机静态服务，访问终端对应的本机地址。不要把真实审查放进site或examples。GitHub Pages和远程CI需要在实际仓库中配置与验证。
