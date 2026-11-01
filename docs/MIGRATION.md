# 从0.1.0迁移至0.2.0

这是评分口径变更，不是简单改版本号。旧报告保留原样；不将旧分数与新分数直接比较。

旧版：指标分配weight并凑满维度分数；failed检查的分值形成扣分。新版：只有维度有weight；每维度满分100，确认的独立问题按severity扣分。多个独立问题命中同一指标时也分别扣分。

结构变化：schema_version 1.0→2.0，rubric_version 2.0→3.0，新增policy_version 1.0。检查删除weight，finding_id改为finding_ids数组。问题增加criterion_ids、severity_reason；阻断增加blocker_rule_id和blocker_reason。critical_gate改为指标critical_review，不再让关键指标失败自动触发阻断。

处理步骤：保存旧包与旧报告；使用新版init生成全unknown草稿；重新确认基线、适用性和范围；复核可复用证据，按独立根因合并或拆分问题；为严重度和阻断补齐判断依据；运行validate和render。不能机械把旧扣分换算成新版严重度。

新版拒绝旧输入并给出错误，不自动伪造检查结果。未完成检查只展示暂评上限，旧版按指标权重推导的分数区间不再沿用。规则快照与哈希随新报告归档。
