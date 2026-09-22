# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 非 Databricks JDBC URL 在创建连接前被拒绝 | 已准备一个不属于 `jdbc:databricks://` 协议的 JDBC URL。 | 客户端请求创建 Databricks 数据源连接。 | 服务端在真正创建连接前判定该 URL 不属于 Databricks JDBC 协议。<br>错误消息包含「The JDBC URL must use the jdbc:databricks:// protocol.」。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-002 | TG-002 | 合法的自定义 Databricks JDBC URL 继续建立连接 | 已准备以 `jdbc:databricks://` 开头且其余连接参数合法的自定义 URL。 | 客户端请求创建 Databricks 数据源连接。 | URL 通过协议校验，并继续进入 Databricks 连接流程。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-003 | TG-003 | Databricks URL 只交由 Databricks JDBC driver 处理 | 系统同时注册 Databricks JDBC driver 和其他 JDBC driver。<br>分别准备合法 Databricks URL 与非 Databricks URL。 | 客户端分别请求创建 Databricks 数据源连接。 | 合法 URL 由 Databricks JDBC driver 处理。<br>非 Databricks URL 被拒绝后，不会转交其他已注册 driver。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-004 | TG-004 | Databricks JDBC driver 拒绝 URL 时失败关闭 | 已构造 Databricks JDBC driver 明确拒绝 URL 的结果。 | 客户端请求创建 Databricks 数据源连接。 | 服务端返回连接创建错误。<br>连接流程停止，且不会返回连接成功。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-005 | TG-005 | 既有合法 Databricks 配置使用明确的 JDBC token 属性 | 已准备升级前可用的 Databricks 配置、合法 JDBC URL 与当前 token 认证信息。 | 安装或升级后的系统使用该配置创建连接。 | 提交给 JDBC driver 的属性 `UID` 等于 {token}。<br>属性 `PWD` 等于当前 token 值。<br>既有合法配置能够建立连接，其原有成功行为不回退。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-006 | TG-006 | URL 校验失败时不连接错误目标 | 已准备一个非 Databricks JDBC URL，并启用对 driver 或网络连接调用的观测。 | 客户端请求创建 Databricks 数据源连接。 | URL 校验在连接创建阶段失败。<br>失败前后均未向该错误目标建立网络连接。 | 服务端连接层 | business_behavior | confirmed |  |
| AE-007 | TG-004 | Databricks JDBC driver 返回空连接时失败关闭 | 已构造 Databricks JDBC driver 接受 URL 但返回空连接的结果。 | 客户端请求创建 Databricks 数据源连接。 | 服务端返回连接创建错误。<br>连接流程停止，且不会返回连接成功。 | 服务端连接层 | business_behavior | confirmed |  |
