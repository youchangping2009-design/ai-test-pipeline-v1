# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 写入优先使用显式 Serializer | APIStore 已配置可记录调用的显式 Serializer，并准备一个可写入对象。 | 通过 APIStore 写入该对象。 | 写入数据由显式 Serializer 编码。<br>已配置 codec 不参与本次写入编码。 | APIStore 写入与序列化调用层 | backend_job | confirmed |  |
| AE-002 | TG-001 | 单条读取优先使用显式 Serializer | APIStore 已配置可记录调用的显式 Serializer，且存储中存在目标对象。 | 通过 APIStore 单条读取目标对象。 | 目标对象由显式 Serializer 解码。<br>已配置 codec 不参与本次解码。 | APIStore 单条读取与序列化调用层 | backend_job | confirmed |  |
| AE-003 | TG-001 | 列表读取优先使用显式 Serializer | APIStore 已配置可记录调用的显式 Serializer，且存储中存在多个目标对象。 | 通过 APIStore 列表读取目标对象。 | 列表中的对象由显式 Serializer 解码。<br>已配置 codec 不参与本次列表解码。 | APIStore 列表读取与序列化调用层 | backend_job | confirmed |  |
| AE-004 | TG-001 | watch 解码优先使用显式 Serializer | APIStore 已配置可记录调用的显式 Serializer，并已建立目标资源的 watch。 | 存储层向 watch 投递对象事件。 | watch 事件对象由显式 Serializer 解码。<br>已配置 codec 不参与本次 watch 解码。 | APIStore watch 与序列化调用层 | backend_job | confirmed |  |
| AE-005 | TG-002 | 默认写入声明 GVK 时使用直接 JSON | APIStore 未配置显式 Serializer，并准备一个使用声明 GVK 的对象。 | 通过 APIStore 写入该对象。 | 对象以直接 JSON 方式编码并写入。<br>已配置 codec 不参与本次写入编码。 | APIStore 默认写入序列化分支 | backend_job | confirmed |  |
| AE-006 | TG-002 | 默认写入其他 GVK 时使用 codec | APIStore 未配置显式 Serializer，已配置可记录调用的 codec，并准备一个非声明 GVK 的对象。 | 通过 APIStore 写入该对象。 | 对象由已配置 codec 编码并写入。<br>本次写入不使用声明 GVK 的直接 JSON 分支。 | APIStore 默认写入序列化分支 | backend_job | confirmed |  |
| AE-007 | TG-003 | 默认单条读取使用 codec | APIStore 未配置显式 Serializer，已配置可记录调用的 codec，且存储中存在目标对象。 | 通过 APIStore 单条读取目标对象。 | 目标对象由已配置 codec 解码。 | APIStore 默认单条读取分支 | backend_job | confirmed |  |
| AE-008 | TG-003 | 默认列表读取使用 codec | APIStore 未配置显式 Serializer，已配置可记录调用的 codec，且存储中存在多个目标对象。 | 通过 APIStore 列表读取目标对象。 | 列表中的对象由已配置 codec 解码。 | APIStore 默认列表读取分支 | backend_job | confirmed |  |
| AE-009 | TG-003 | 默认 watch 解码使用 codec | APIStore 未配置显式 Serializer，已配置可记录调用的 codec，并已建立目标资源的 watch。 | 存储层向 watch 投递对象事件。 | watch 事件对象由已配置 codec 解码。 | APIStore 默认 watch 解码分支 | backend_job | confirmed |  |
| AE-010 | TG-004 | 通用 JSON Serializer 往返保留对象 GVK | 准备一个已设置 GVK 的 datasource 对象和通用 JSON Serializer。 | 使用该 Serializer 编码对象后再解码。 | 解码后对象的 GVK 与编码前完全一致。 | datasource JSON Serializer 往返层 | backend_job | confirmed |  |
| AE-011 | TG-005 | 同一 Go 类型的不同 GVK 往返后仍可区分 | 准备两个 Go 类型相同但 GVK 不同的对象。 | 分别持久化并读回两个对象。 | 两个读回对象各自保留原 GVK。<br>两个对象不会因 Go 类型相同而被识别为同一 GVK。 | APIStore 持久化与对象身份层 | backend_job | confirmed |  |
| AE-012 | TG-006 | watch 当前对象解码沿用请求 context | 建立带可识别值的请求 context，并让 watch 事件包含当前对象。 | watch 解码当前对象。 | 当前对象的解码调用收到原请求 context。 | APIStore watch 当前对象解码层 | backend_job | confirmed |  |
| AE-013 | TG-006 | watch 历史对象解码沿用请求 context | 建立带可识别值的请求 context，并让 watch 事件包含历史对象。 | watch 解码历史对象。 | 历史对象的解码调用收到原请求 context。 | APIStore watch 历史对象解码层 | backend_job | confirmed |  |
| AE-014 | TG-006 | 取消 watch 请求会终止相关解码 | 已建立一个正在等待或执行对象解码的 watch 请求。 | 取消该 watch 请求的 context。 | 相关解码工作观察到取消并终止。<br>请求取消后不继续处理后续对象。 | APIStore watch 生命周期层 | backend_job | confirmed |  |
| AE-015 | TG-012 | 写入时显式 Serializer 接收原请求 context | APIStore 已配置可记录 context 的显式 Serializer，并建立带可识别值的请求 context。 | 使用该请求 context 通过 APIStore 写入对象。 | 写入编码调用的显式 Serializer 收到原请求 context。 | APIStore 写入与请求上下文层 | backend_job | confirmed |  |
| AE-016 | TG-012 | 单条读取时显式 Serializer 接收原请求 context | APIStore 已配置可记录 context 的显式 Serializer，存储中存在目标对象，并建立带可识别值的请求 context。 | 使用该请求 context 通过 APIStore 单条读取目标对象。 | 单条读取解码调用的显式 Serializer 收到原请求 context。 | APIStore 单条读取与请求上下文层 | backend_job | confirmed |  |
| AE-017 | TG-012 | 列表读取时显式 Serializer 接收原请求 context | APIStore 已配置可记录 context 的显式 Serializer，存储中存在多个目标对象，并建立带可识别值的请求 context。 | 使用该请求 context 通过 APIStore 列表读取目标对象。 | 列表中每个对象的解码调用均由显式 Serializer 收到原请求 context。 | APIStore 列表读取与请求上下文层 | backend_job | confirmed |  |
