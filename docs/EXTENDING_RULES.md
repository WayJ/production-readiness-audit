# 扩展指标 / Extending rules

## 两个源文件

`skills/production-readiness-audit/assets/scoring-rubric.json` 是维度及指标定义的唯一来源；`scoring-policy.json` 是扣分策略的唯一来源。只有维度拥有 `weight`，所有维度合计100。单个指标禁止 `weight` 或 `points`。

`audit.schema.json`、`audit.blank.json`、`references/diagnostic-checks.md` 自动生成，不要手改。

## 新增一个指标

在某维度的 `criteria` 中添加唯一ID，并升级 `rubric_version`。例如在D维度添加：

```json
{
  "id": "D4",
  "title": "测试替身与真实依赖的边界",
  "critical_review": false,
  "applicability": "存在测试替身或可替换依赖的项目。",
  "requirement": "检查生产路径是否意外使用测试实现、模拟持久化或假成功返回。",
  "proof": "定位依赖装配和配置分支，并在授权隔离环境核对实际运行路径。",
  "pass_condition": "生产路径使用真实有效的依赖；替身仅在明确测试范围装配。",
  "fail_condition": "有证据证明测试替身进入正式运行路径并影响行为。",
  "deduplication": "同一错误装配导致多入口使用替身时合并为一个根因。"
}
```

这只是可选扩展示例，不是已经加入默认量表的第28项。维度权重仍为10；其余指标不改分数。

执行：

```sh
python scripts/review.py sync-rules
python scripts/review.py sync-rules --check
python scripts/review.py init --project "新审查" --output review-data/new-audit.json
```

新指标自动出现在Schema、空白草稿和检查说明中，默认unknown。`--check`只检查生成物漂移，不写文件。核心运行时从实际源文件读取ID，不依赖固定27项或固定编号枚举。

## 现有项目与测试样例

旧报告保留旧版本。不能把量表版本号直接改成新版本就当作已检查。使用新的空白草稿重新确认范围；可复用的旧证据需要重新核对，新增指标保持unknown直到审查。

仓库示例是人工维护的合成测试数据，不会被同步命令偷偷写成pass。变更默认量表时，需要为示例增加对应unknown记录、更新版本字段、更新适用的测试断言，再运行测试和网站构建。日常只新增指标不需改HTML或评分核心。

## 多个检查与多个问题

同一指标可以有多个检查记录，例如E3.1和E3.2，均引用 `criterion: "E3"`。没有子项分值。只要一个适用子检查仍unknown，整个原始指标的验证就未完成；拆分数量不会稀释风险或提高完成度。

失败检查使用 `finding_ids` 数组，可关联多个独立根因。问题使用 `criterion_ids`，可关联多个指标。双向关系和证据必须一致。相同 `root_cause_key` 不允许出现两条问题；先合并再计分。

## 扣分与阻断

问题的 `severity` 从策略决定维度内扣分，必须填写 `severity_reason`。不能输入points覆盖分值。调整扣分档位时升级 `policy_version`。

`critical_review` 仅标识关键未知，不意味着失败必然阻断。确认阻断需要 `blocker: true`、有效 `blocker_rule_id`、`blocker_reason`、确认状态和支持证据。不同阻断规则允许的主维度由策略定义。

## 版本复现

报告内嵌 `summary.rule_snapshot.rubric` 和 `summary.rule_snapshot.policy`，并保存各自的SHA-256。保存为两个JSON后，复算时指定：

```sh
python scripts/review.py render --input old-audit.json --rubric frozen-rubric.json --policy frozen-policy.json --output reports/reproduced.html
```

规则快照支持复算，但不能证明证据本身真实。归档时同时保存原始输入、报告、相关工具版本和证据。

## English summary

Add an unweighted criterion to the rubric, bump its version, run `sync-rules`, and create a new review. Only dimension weights total 100. Criterion pass states never add points. Penalties belong to confirmed root-cause findings and the independent policy. Generated schema, blank input and reference documentation stay synchronized; the renderer and scorer need no per-criterion code changes. Existing evidence and synthetic fixtures require deliberate review, never silent passes.
