# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 外部撤销记录仅合并任务 ID | 来源 Worker 或持久化状态包含撤销任务 ID 及来源主机的 monotonic 时间戳。 | 本机 Worker 接收并合并该撤销状态。 | 本机撤销集合包含收到的任务 ID。<br>该记录不复用来源主机的 monotonic 时间戳。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
| AE-002 | TG-002 | 外部撤销 ID 按本机接收时间计算有效期 | 本机 Worker 配置了 `REVOKE_EXPIRES`，并记录接收外部撤销 ID 的本机时刻。 | 在有效期内及有效期结束后分别检查该撤销 ID。 | 从本机接收时刻起的有效期内该 ID 保持撤销。<br>超过 `REVOKE_EXPIRES` 后该 ID 从撤销集合移除。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
| AE-003 | TG-003 | 满容量时保留本机新撤销任务 | 撤销集合已达到 `maxlen`，其中包含从外部接收的撤销记录。 | 本机新增一个撤销任务 ID。 | 本机刚新增的撤销任务 ID 仍保留在集合中。<br>外部时间戳排序不会错误驱逐该本机新记录。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
| AE-004 | TG-003 | 有效期内已撤销 ETA 或 countdown 任务不执行 | ETA 或 countdown 任务的 ID 已在本机撤销集合中，且撤销记录仍在有效期内。 | 任务到达预定执行时间。 | 任务不执行。<br>任务对应的业务副作用不发生。 | 服务端 Celery Worker 执行层 | backend_job | confirmed |  |
| AE-005 | TG-004 | hello 同步按本机时间重新计时 | 远端 Worker 已持有待同步的撤销任务 ID。 | 本机通过 hello 接收该撤销 ID。 | hello 同步载荷仅包含任务 ID，不包含远端 monotonic 时间戳。<br>撤销 ID 从本机接收时刻开始计算有效期。 | 服务端 Celery Worker 同步层 | backend_job | confirmed |  |
| AE-006 | TG-004 | mingle 同步按本机时间重新计时 | 远端 Worker 已持有待同步的撤销任务 ID。 | 本机通过 mingle 接收该撤销 ID。 | mingle 同步载荷仅包含任务 ID，不包含远端 monotonic 时间戳。<br>撤销 ID 从本机接收时刻开始计算有效期。 | 服务端 Celery Worker 同步层 | backend_job | confirmed |  |
| AE-007 | TG-004 | statedb 恢复按本机时间重新计时 | `--statedb` 中持久化了撤销任务 ID 和原进程的 monotonic 时间戳。 | Worker 启动并从 `--statedb` 恢复撤销状态。 | 恢复的撤销 ID 从本机恢复时刻开始计算有效期。<br>持久化的旧 monotonic 时间戳不决定本机过期顺序。 | 服务端 Celery Worker 持久化恢复层 | backend_job | confirmed |  |
| AE-008 | TG-005 | 新旧 Worker 双向交换不丢失撤销 ID | 滚动升级集群中同时存在新旧 Worker，两端各自持有不同的撤销任务 ID。 | 新旧 Worker 双向交换撤销状态。 | 双向同步载荷仅包含任务 ID，不包含任一 Worker 的 monotonic 时间戳。<br>交换完成后，新旧 Worker 的撤销集合均包含双方提供的任务 ID。 | 服务端 Celery 混合集群状态层 | backend_job | confirmed |  |
| AE-009 | TG-006 | 边界：now 为 0 时撤销记录可加入和排序 | 撤销集合的当前时间输入为 `now=0`。 | 向集合加入撤销任务 ID 并执行排序。 | 加入后撤销集合包含该任务 ID。<br>排序过程不抛出异常。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
| AE-010 | TG-006 | 边界：相同时间戳的撤销记录排序稳定 | 撤销集合中存在多条 monotonic 时间戳相同的记录。 | 集合执行排序和容量维护。 | 排序过程不抛出异常。<br>相同时间戳的记录仍可被稳定保留和处理。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
| AE-011 | TG-006 | 边界：混合类型任务 ID 不触发比较异常 | 撤销集合同时包含整数任务 ID 和字符串任务 ID。 | 集合加入、排序并清理这些撤销记录。 | 集合操作不触发任务 ID 类型比较异常。 | 服务端 Celery Worker 状态层 | backend_job | confirmed |  |
