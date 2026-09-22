# 两批 7 份公开盲测遗留问题评估

日期：2026-09-21

## 完成状态

- 第一批 3 份（Appsmith、Chatwoot、Saleor）已完成反馈回灌、重生成、Oracle 复测和 Strict Gate，已闭环。
- 第二批 4 份（Django、Celery、Temporal、Supabase）已完成首次生成、资产冻结、Oracle Review 和反馈分流，尚未闭环。
- 第二批剩余正式阶段：设计层反馈应用与重生成、Oracle 复评分、Strict Gate、项目级收口报告。

## 已修复的通用问题

第一批及第二批前序阶段已修复领域模板污染、来源范围误提升、复合规则未原子化、direct renderer 错用 UI 模板、验证侧/类型误判、纯文本图片门禁误阻断、Harness checkpoint 恢复以及显式基线比较误报等问题。现有 7 个样本均未再次出现 PT083 领域词污染，当前正式 testcase 相关率没有新增范围过伸。

## 仍需修复的项目问题

| 优先级 | 问题 | 证据 | 建议 |
|---|---|---|---|
| P1 | Oracle 单一覆盖率混合了批准需求、实现细节和运维风险 | Temporal/Supabase 因动态开关、错误路径和 UI 交互被同等扣分 | 为 assertion 增加 `requirement` / `implementation` / `risk` scope，分别出分 |
| P1 | Harness Review checkpoint 没有执行确定性检查 | 当前 review stage 使用 `_no_commands`，文件存在即可 succeeded | 接入 design feedback validator、Oracle delta scorer 和冻结哈希校验 |
| P1 | 反馈回灌与重生成仍主要依赖人工编排 | 第一批能闭环，但需要手工更新多层设计资产并重跑 | 增加受限 feedback-apply 流程，强制从设计层修改并保留前后 diff |
| P2 | Oracle assertion 到设计层的来源范围没有机器约束 | 目前依赖人工把实现独有项留在 risk/audit | 在 design feedback/schema 中持久化 source_scope，并阻止 oracle-only 自动进入 product_acceptance |
| P2 | 盲测只有 L0/L1 静态映证 | 7 个上游仓库均未在本地执行真实测试 | 为可承受样本增加可复现 checkout、依赖缓存和目标测试命令 |
| P2 | 样本数量和类遗留型仍有限 | 目前只有 7 份公开 PR | 在完成本批闭环后继续加入权限、并发、数据迁移、异步与跨端样本 |

## 不应误判为流水线缺陷的事项

- 需求输入没有描述的内部异常、动态开关或 UI 微交互，不应在盲生成阶段自动出现；由后置代码 Review 识别是正常流程。
- Supabase 功能关闭跳转与批准需求冲突属于实现差异，不应通过修改测试预期“修复”。
- 回灌后 Oracle coverage 达到 1.0 只证明当前固定 Oracle 已闭环，不证明未知行为全部覆盖。

## 当前判断

项目主流程已经能稳定生成可追溯且范围相关的用例，但仍不适合宣称“盲测体系完全闭环”。最关键的遗留是 Oracle 分层计分、Review 阶段机器门禁和反馈回灌自动化；第二批四份样本也必须完成重生成、复评分和 Strict Gate 后才能标记整轮完成。

## 2026-09-22 修复进展

Oracle 分层计分已完成：7 份样本全部复算，旧输入兼容通过。Temporal/Supabase requirement coverage 均校正为 `1.0`，实现/风险缺口独立展示；当前该项不再是遗留问题。剩余最高优先级为 Review checkpoint 机器门禁和反馈回灌自动化。
