# Analysis Report

## Requirement Summary
- 标题：`CELERY-10668 跨 Worker 时钟域保留撤销任务需求整理`
- 摘要：Worker 从其他主机或持久化状态接收已撤销任务时，不得直接复用来源主机的 monotonic 时间戳。接收的任务 ID 应在本机时钟域重新建立有效期，避免外部时间戳长期占满撤销集合并驱逐本机新撤销任务。被撤销的 ETA/countdown 任务在有效期内不得执行。
- 主要页面数：0
- 主要展示面数：0

## Reasoning Snapshot
- explicit_rules：16
- implicit_rules：0
- field_constraints：0
- data_source_rules：0
- business_risks：4
- edge_cases：1
- ambiguities：4
- recommended_test_dimensions：7
- coverage_candidates：16

## Top Explicit Rules
- `ER-001` Worker 从其他主机或持久化状态接收已撤销任务时，不得直接复用来源主机的 monotonic 时间戳。接收的任务 ID 应在本机时钟域重新建立有效期，避免外部时间戳长期占满撤销集合并驱逐本机新撤销任务。被撤销的 ETA/countdown 任务在有效期内不得执行。
- `ER-002` 外部撤销状态只以任务 ID 参与合并，不把外部 monotonic 时间戳作为本机有效期依据。
- `ER-003` 接收的任务 ID 从本机收到时开始计算撤销有效期。
- `ER-004` 集合达到容量时，本机刚撤销的任务不得被错误驱逐。
- `ER-005` `hello`、mingle 和 `--statedb` 三条入口保持一致语义。
- `ER-006` 新旧 Worker 混合集群应能兼容两种撤销状态表示。
- `ER-007` 同一时刻加入不同类型任务 ID 时不得因比较 ID 类型产生错误。
- `ER-008` 来源 Worker 时间戳明显领先时，接收 Worker 仍按本机时间处理撤销状态。

## Top Implicit Rules

## Key Risks
- `RISK-001` [medium] 滚动升级期间旧 Worker 与新 Worker 的状态格式兼容是核心风险。
- `RISK-002` [high] 重新从接收时间计算有效期会延长部分撤销 ID 的存活时间，但优先保证不错误执行任务。
- `RISK-003` [medium] 高频撤销和满容量条件下才容易暴露驱逐问题，普通小样本可能产生假通过。
- `RISK-004` [medium] 跨主机 monotonic 时钟不可比较，测试不能用墙钟调整替代真实时钟域差异。

## Ambiguities
- `AMB-001` 新旧版本兼容范围覆盖哪些 Celery 版本？
- `AMB-002` 接收后的撤销有效期延长是否有可接受的最大边界？
- `AMB-003` 重复接收相同撤销 ID 是否重置本地有效期？
- `AMB-004` 集群中撤销状态交换的最大载荷或性能阈值未说明。

## Recommended Test Dimensions
- `TD-001` 显式规则逐条验证：需求摘要已给出可追溯规则，后续设计应保持单规则单断言并验证成功与失败结果。
- `TD-002` 异常与失败处理：需求包含明确拒绝或失败语义，需要验证失败状态、错误反馈及副作用隔离。
- `TD-003` 兼容性与回归：需求要求保留既有合法行为或历史关系，需要同时验证变更路径与未变路径。
- `TD-004` 数据一致性与状态保留：需求涉及关系或状态保留，应核对操作前后数据集合而非只看接口成功。
- `TD-005` 输入类型与边界：输入的类型、边界值和协议格式会影响判断结果，需要覆盖合法、非法及临界输入。
- `TD-006` 风险与非功能约束：需求摘要已明确兼容性、性能或一致性风险，需与产品验收规则分层承接。
- `TD-007` 未决项追踪：摘要存在尚未确认的输入或验收口径，后续不得将其自动升级为强制规则。
