# Testpoints View

- Project: `OSS-BLIND`
- Work Item: `APPSMITH-42244`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | field_rule | 非 Databricks JDBC URL 在连接创建前被拒绝 | 非 `jdbc:databricks://` 协议 URL 在真正创建连接前被拒绝，错误消息包含「The JDBC URL must use the jdbc:databricks:// protocol.」。 | P0 | CP-001 | True |
| TP-002 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | field_rule | 合法自定义 Databricks JDBC URL 进入连接流程 | 以 `jdbc:databricks://` 开头且参数合法的自定义 URL 通过协议校验并继续建立连接。 | P0 | CP-002 | True |
| TP-003 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | cross_surface_linkage | Databricks URL 由指定 driver 处理且拒绝后不回退 | 合法 URL 仅交由 Databricks JDBC driver 处理，非 Databricks URL 被拒绝后不转交其他 driver。 | P0 | CP-003 | True |
| TP-004 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | field_rule | Databricks JDBC driver 拒绝 URL 时返回创建错误 | Databricks JDBC driver 拒绝 URL 时返回连接创建错误、停止后续行为且不判为成功。 | P0 | CP-004 | True |
| TP-005 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | cross_surface_linkage | 既有合法配置使用明确的 JDBC token 属性建立连接 | JDBC 连接属性 `UID` 固定为 {token}，`PWD` 等于当前 token 值，既有合法配置仍可成功连接。 | P1 | CP-005 | True |
| TP-006 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | cross_surface_linkage | URL 校验失败不产生错误目标网络连接 | 非 Databricks URL 在连接创建阶段校验失败，且不会向错误目标建立网络连接。 | P0 | CP-006 | True |
| TP-007 | Databricks 数据源配置页 | 连接配置区 | Databricks 数据源连接 | 自定义 JDBC URL 连接创建 | field_rule | Databricks JDBC driver 返回空连接时返回创建错误 | Databricks JDBC driver 返回空连接时返回连接创建错误、停止后续行为且不判为成功。 | P0 | CP-007 | True |
