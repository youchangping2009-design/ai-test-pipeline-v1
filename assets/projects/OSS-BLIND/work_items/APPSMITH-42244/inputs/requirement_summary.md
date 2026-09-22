# APPSMITH-42244 Databricks JDBC URL validation 需求整理

整理时间：2026-09-21

## 1. 资料来源

- Appsmith GitHub PR #42244，状态为已合并，目标分支为 `release`。
- 本地冻结快照：`inputs/public_source_snapshot.md`。
- PR 引用的 Linear APP-15972 无公开访问内容；安全公告细节本轮未成功取得。
- 为保持盲测，代码 diff 与 PR 内新增测试不作为需求输入。

## 2. 需求结论

Databricks 插件在建立数据源连接前必须验证自定义 JDBC URL。非 Databricks URL 应被拒绝；有效的 Databricks URL，包括既有自定义 `jdbc:databricks://` 配置，应继续正常建立连接。连接应由 Databricks JDBC driver 直接处理，并在 driver 拒绝 URL 时采用失败关闭策略。

## 3. 前置条件 / 准备工作

- 可创建或编辑 Appsmith Databricks 数据源。
- 准备有效 Databricks 连接配置、有效 token 和可连接环境。
- 准备至少一个非 Databricks JDBC URL，用于验证连接创建前拦截。
- 测试入口关注 `DatabricksPluginExecutor.datasourceCreate`，但不将实现方式当作唯一业务断言。

## 4. 业务范围与不做范围

范围内：自定义 JDBC URL 的协议归属校验、driver 接受或拒绝结果、有效配置兼容性，以及失败时不转交其他 JDBC driver 建连。

范围外：不修改已有数据或配置结构；不要求迁移；不根据不可访问的安全公告推断攻击方式或影响版本；不扩展到其他数据库插件。

## 5. 面向研发的需求拆解

- 在真正创建连接之前检查 URL 是否属于 Databricks JDBC 协议。
- 连接由明确的 Databricks JDBC driver 处理。
- URL 被校验逻辑或 driver 拒绝时，返回连接创建错误并停止后续连接行为。
- 有效 URL 继续使用当前认证信息建立连接，不改变既有合法配置行为。

## 6. 面向测试的验收关注点

- 非 Databricks JDBC URL 被拒绝，且不会被其他已注册 driver 接管。
- 有效 `jdbc:databricks://` URL 可以进入 Databricks driver 的连接流程。
- 自定义但合法的 Databricks URL 保持兼容。
- driver 明确拒绝 URL 或无法返回连接时，系统不得把连接创建判为成功。
- 既有有效安装和升级场景行为不回退。
- 验证失败发生在连接创建阶段，不应先对错误目标建立网络连接。

## 7. 数据 / 埋点 / 接口 / 配置要求

- 关键输入：Databricks 数据源的 JDBC URL 与 token 认证信息。
- 已知合法协议前缀：`jdbc:databricks://`。
- PR 未声明新增 API 字段、数据库迁移、埋点或持久化配置。

## 8. 风险与兼容性

- 仅检查字符串前缀可能遗漏大小写、前后空白、编码或相似协议边界，应由后续设计区分正式验收与风险加固。
- driver 返回空连接、抛出异常和拒绝 URL 的错误口径尚未完全定义。
- 历史非 Databricks URL 配置会从可尝试连接变为明确失败，这是预期行为变化。

## 9. 待确认问题

- 空 URL、纯空白 URL、大小写变化和前导空白是否统一按非法处理？
- 失败时的正式错误码和用户可见文案是什么？
- URL 参数、端口、catalog/schema 和编码边界由插件还是 driver 最终判定？
- 安全公告的具体威胁模型和受影响版本未公开取得。

## 10. 本轮整理边界

本摘要只基于公开 PR 描述冻结需求输入。代码差异和已有测试作为后续盲测评分 oracle，不进入本阶段输入，也不生成 Structured PRD、Case Plan 或测试用例。
