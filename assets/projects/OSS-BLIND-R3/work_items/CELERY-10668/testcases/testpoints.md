# Testpoints View

- Project: `OSS-BLIND-R3`
- Work Item: `CELERY-10668`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | data_persistence | 外部撤销记录仅合并任务 ID | 本机撤销集合包含收到的任务 ID；该记录不复用来源主机的 monotonic 时间戳。 | P0 | CP-001 | True |
| TP-002 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | 外部撤销 ID 按本机接收时间计算有效期 | 从本机接收时刻起的有效期内该 ID 保持撤销；超过 `REVOKE_EXPIRES` 后该 ID 从撤销集合移除。 | P0 | CP-002 | True |
| TP-003 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | 满容量时保留本机新撤销任务 | 本机刚新增的撤销任务 ID 仍保留在集合中；外部时间戳排序不会错误驱逐该本机新记录。 | P0 | CP-003 | True |
| TP-004 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | 有效期内已撤销 ETA 或 countdown 任务不执行 | 任务不执行；任务对应的业务副作用不发生。 | P0 | CP-004 | True |
| TP-005 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | hello 同步按本机时间重新计时 | hello 同步载荷仅包含任务 ID，不包含远端 monotonic 时间戳；收到的撤销 ID 从本机接收时刻开始计算有效期。 | P0 | CP-005 | True |
| TP-006 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | mingle 同步按本机时间重新计时 | mingle 同步载荷仅包含任务 ID，不包含远端 monotonic 时间戳；收到的撤销 ID 从本机接收时刻开始计算有效期。 | P0 | CP-006 | True |
| TP-007 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | backend_job | statedb 恢复按本机时间重新计时 | 恢复的撤销 ID 从本机恢复时刻开始计算有效期；持久化的旧 monotonic 时间戳不决定本机过期顺序。 | P0 | CP-007 | True |
| TP-008 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | cross_surface_linkage | 新旧 Worker 双向交换不丢失撤销 ID | 双向同步载荷仅包含任务 ID，不包含任一 Worker 的 monotonic 时间戳；交换完成后，新旧 Worker 的撤销集合均包含双方提供的任务 ID。 | P0 | CP-008 | True |
| TP-009 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | field_rule | 边界：now 为 0 时撤销记录可加入和排序 | 加入后撤销集合包含该任务 ID；排序过程不抛出异常。 | P0 | CP-009 | True |
| TP-010 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | field_rule | 边界：相同时间戳的撤销记录排序稳定 | 排序过程不抛出异常；相同时间戳的记录仍可被稳定保留和处理。 | P0 | CP-010 | True |
| TP-011 | Celery Worker 撤销状态处理 | 撤销状态合并与执行保护 | Worker 撤销状态 | 跨时钟域撤销状态合并 | field_rule | 边界：混合类型任务 ID 不触发比较异常 | 集合操作不触发任务 ID 类型比较异常。 | P0 | CP-011 | True |
