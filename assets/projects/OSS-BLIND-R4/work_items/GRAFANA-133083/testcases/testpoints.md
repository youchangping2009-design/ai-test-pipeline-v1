# Testpoints View

- Project: `OSS-BLIND-R4`
- Work Item: `GRAFANA-133083`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 写入优先使用显式 Serializer | 写入数据由显式 Serializer 编码；已配置 codec 不参与本次写入编码。 | P0 | CP-001 | True |
| TP-002 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 单条读取优先使用显式 Serializer | 目标对象由显式 Serializer 解码；已配置 codec 不参与本次解码。 | P0 | CP-002 | True |
| TP-003 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 列表读取优先使用显式 Serializer | 列表中的对象由显式 Serializer 解码；已配置 codec 不参与本次列表解码。 | P0 | CP-003 | True |
| TP-004 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | watch 解码优先使用显式 Serializer | watch 事件对象由显式 Serializer 解码；已配置 codec 不参与本次 watch 解码。 | P0 | CP-004 | True |
| TP-005 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 默认写入声明 GVK 时使用直接 JSON | 对象以直接 JSON 方式编码并写入；已配置 codec 不参与本次写入编码。 | P0 | CP-005 | True |
| TP-006 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 默认写入其他 GVK 时使用 codec | 对象由已配置 codec 编码并写入；本次写入不使用声明 GVK 的直接 JSON 分支。 | P0 | CP-006 | True |
| TP-007 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 默认单条读取使用 codec | 目标对象由已配置 codec 解码。 | P0 | CP-007 | True |
| TP-008 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 默认列表读取使用 codec | 列表中的对象由已配置 codec 解码。 | P0 | CP-008 | True |
| TP-009 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 默认 watch 解码使用 codec | watch 事件对象由已配置 codec 解码。 | P0 | CP-009 | True |
| TP-010 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | data_persistence | 通用 JSON Serializer 往返保留对象 GVK | 解码后对象的 GVK 与编码前完全一致。 | P0 | CP-010 | True |
| TP-011 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | cross_surface_linkage | 同一 Go 类型的不同 GVK 往返后仍可区分 | 持久化与读回完成后，两个对象各自保留原 GVK；两个对象不会因 Go 类型相同而被识别为同一 GVK。 | P0 | CP-011 | True |
| TP-012 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | Watch 上下文传播 | backend_job | watch 当前对象解码沿用请求 context | 当前对象的解码调用收到原请求 context。 | P0 | CP-012 | True |
| TP-013 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | Watch 上下文传播 | backend_job | watch 历史对象解码沿用请求 context | 历史对象的解码调用收到原请求 context。 | P0 | CP-013 | True |
| TP-014 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | Watch 上下文传播 | backend_job | 取消 watch 请求会终止相关解码 | 相关解码工作观察到取消并终止；请求取消后不继续处理后续对象。 | P0 | CP-014 | True |
| TP-015 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 写入时显式 Serializer 接收原请求 context | 写入编码调用的显式 Serializer 收到原请求 context。 | P0 | CP-015 | True |
| TP-016 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 单条读取时显式 Serializer 接收原请求 context | 单条读取解码调用的显式 Serializer 收到原请求 context。 | P0 | CP-016 | True |
| TP-017 | APIStore 资源序列化 | 序列化选择与对象往返 | APIStore 序列化 | 资源序列化选择 | backend_job | 列表读取时显式 Serializer 接收原请求 context | 列表中每个对象的解码调用均由显式 Serializer 收到原请求 context。 | P0 | CP-017 | True |
