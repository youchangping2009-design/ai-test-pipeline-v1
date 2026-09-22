# Appsmith #42244 盲测 Oracle 对照报告

生成时间：2026-09-21
工作项：OSS-BLIND/APPSMITH-42244
Oracle：[appsmithorg/appsmith#42244](https://github.com/appsmithorg/appsmith/pull/42244)，head `27ef9f61e2e2293b87ecd33728d79d8d84d3fef5`

## 结论摘要

- 建议开始测试。核心改动是前缀预检、指定 Databricks driver 直连、空连接失败和 token 属性传递；6 条盲测用例覆盖主链及错误目标不建连。
- 公开新增测试中的精确错误文案与 `UID/PWD` 属性映射没有被正式用例明确断言；CP-004 还合并了两个失败分支。
- 当前缺口应先反馈到 Case Plan；本报告不修改冻结用例。

## 代码与测试证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `DatabricksPlugin.java` `datasourceCreate` | 空值或非 `jdbc:databricks://` 前缀直接返回参数错误 | CP-001、CP-006 | 命中 |
| `DatabricksPlugin.java` 构造器与 `jdbcDriver.connect` | 使用指定 Databricks driver，不再依赖 `DriverManager` 选择其他 driver | CP-002、CP-003 | 命中 |
| `DatabricksPlugin.java` `connection == null` | driver 不接受 URL 时返回同一参数错误 | CP-004 | 命中但不原子 |
| `DatabricksPluginTest.datasourceCreate_rejectsNonDatabricksJdbcUrl` | 检查精确错误信息且 sentinel driver 未调用 | CP-001、CP-003、CP-006 | 未明确断言错误文案 |
| `DatabricksPluginTest.datasourceCreate_acceptsDatabricksJdbcUrl` | 检查返回连接、`UID=token`、`PWD=test-token` | CP-002、CP-005 | token 语义命中，属性键值不够精确 |

## 问题清单

| 编号 | 严重级别 | 类型 | 问题 | 建议 |
|---|---|---|---|---|
| R1 | Medium | case_gap | CP-001 只断言“连接创建错误”，未锁定新增错误文案。 | 在 Acceptance/Case Plan 增加精确消息断言。 |
| R2 | Medium | case_gap | CP-005 只写“当前 token 认证信息”，未明确 `UID=token`、`PWD=<Bearer Token>`。 | 在 Case Plan 补充属性捕获断言。 |
| R3 | Low-Medium | atomicity | CP-004 将前缀拒绝、driver 拒绝与空连接合并，失败来源不易定位。 | 将前缀校验与 driver 返回 null 拆为原子计划。 |

## AI 本地验证记录

| 验证ID | 级别 | 方法 | 实际结果 | 结论 |
|---|---|---|---|---|
| V-001 | L0 | 固化 8 个盲测产物 SHA-256 | 生成前资产已冻结，oracle 未参与生成 | confirmed_pass |
| V-002 | L1 | GitHub Files API 检查 3 个 changed files、实现补丁与 2 个新增测试 | 6 条用例覆盖核心控制流，存在 R1-R3 | confirmed_gap |
| V-003 | L2 | 上游单测执行 | 当前无 Appsmith 源码 checkout，未在本地执行 | blocked |

## 人工验证重点

1. P0：非 Databricks URL 返回精确错误文案，且抓包/driver spy 证明未发起错误目标连接。
2. P0：合法自定义 URL 通过指定 driver，捕获属性确认 `UID=token`、`PWD` 为输入 token。
3. P1：mock driver 返回 null 与抛出连接异常时分别核对错误类型及后续行为。

## 测试产物影响建议

R1-R3 已写入 `design/design_feedback.json`，目标层为 Acceptance/Case Plan；不得直接覆盖 testcase。

## 反馈实施复测

R1-R3 已全部从设计层应用：精确错误文案与 `UID/PWD` 映射已进入 Acceptance/Case Plan，driver 拒绝与空连接已拆分。重生成后 7 条用例，oracle coverage/relevance 为 `1.0/1.0`。
