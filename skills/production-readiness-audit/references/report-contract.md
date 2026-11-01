# 数据与固定报告契约

审查输入schema_version为2.0，rubric_version与policy_version必须匹配本次规则。

顶层为版本、baseline_ready、meta、conclusion、baseline、checks、findings、evidence。summary是派生值，输入时会被丢弃并重新计算。

检查记录：id、criterion、status(pass/fail/unknown/na)、reason、scope_refs、evidence_ids、finding_ids。没有weight。全部原始指标必须出现，子检查可以增加，但不得遗漏未知。critical和requirement只供派生显示，不能由输入降低规则。

问题记录：id、title、type、dimension_id、criterion_ids、root_cause_key、status(confirmed/unknown)、severity、severity_reason、blocker、blocker_rule_id、blocker_reason、cause、trigger、impact、scope、locations、evidence_ids、suggestion、acceptance。reproduction和priority可选。无points覆盖；同根因重复拒绝。非阻断的blocker_rule_id应为空，blocker_reason应为空字符串。

证据记录：id、method、location、expected、observed、limitations、is_demo。真实报告禁止引用演示证据。Schema负责编辑器结构提示；CLI进一步校验关联、覆盖、范围、证据和去重。

报告固定展示概览、九维评分、确认扣分、问题根因/影响范围/代码证据/建议/复验标准、未知项、基线、全部检查、证据索引、计算规则与版本指纹。维度内扣分与总分影响明确区分。JSON是支撑，不替代HTML。

HTML嵌入数据时转义关闭script及危险字符，界面转义所有用户文本；只许可固定脚本的CSP哈希，无外部网络依赖。实际证据真实性、敏感信息脱敏仍需要审查者负责。
