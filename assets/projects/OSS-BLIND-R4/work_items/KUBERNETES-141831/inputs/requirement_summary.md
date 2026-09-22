# KUBERNETES-141831 Warn on empty DeviceTaintRule selector 需求整理

整理时间：2026-09-22

## 1. 资料来源

- Kubernetes GitHub PR #141831 的公开描述与合并元数据。
- 本地冻结快照：`inputs/public_source_snapshot.md`。
- 为保持盲测，代码 diff、实现 hook、自动化测试和现场验证不作为需求输入。

## 2. 需求结论

- 创建或更新 DeviceTaintRule 时，若 `spec.deviceSelector` 明确存在但 driver、pool、device 均未指定，API 应返回固定文本的非阻塞 Warning；selector 省略或具有有效范围时不告警，既有校验和资源创建/更新结果不改变。

## 3. 前置条件 / 准备工作

- 集群支持 DeviceTaintRule 资源及 create/update 请求。
- 准备 selector 省略、空对象、只指定 driver、只指定 pool、只指定 device 的输入。
- 覆盖不同 taint effect，并准备可读取 HTTP Warning header 的客户端。

## 4. 业务范围与不做范围

- 范围内：create/update 的空 selector 判断、Warning header 文本、非阻塞语义、不同 effect 与客户端告警处理。
- 范围外：把警告升级为校验错误、增加确认步骤、改变设备匹配/taint 执行逻辑，以及修改既有 `effect: None` 预览行为。

## 5. 面向研发的需求拆解

- 仅当 `spec.deviceSelector` 存在且 driver、pool、device 全为空时发出警告。
- create 与 update 使用相同判断和警告文本。
- 精确警告文本为：`spec.deviceSelector: an empty selector matches every device from every driver in the cluster`。
- selector 省略时不告警；任一范围字段已指定时不告警。
- 警告不阻止请求成功，不改变验证结果、持久化结果或后续 taint 行为。
- 判断不应因 taint effect 不同而失效。

## 6. 面向测试的验收关注点

- create 空对象 selector：返回精确 Warning，资源仍成功创建。
- update 为/保持空对象 selector：返回相同 Warning，更新仍成功。
- selector 省略：create/update 均无该 Warning。
- 分别指定 driver、pool、device：均无空 selector Warning。
- 对不同 effect 的空 selector 都告警，包括仅用于预览的既有取值。
- 普通客户端看到警告但请求成功；`kubectl --warnings-as-errors` 可返回非零状态，同时服务端对象确实已创建。
- 其他字段校验失败时，不得因本警告掩盖原有错误。

## 7. 数据 / 埋点 / 接口 / 配置要求

- 资源字段：`DeviceTaintRule.spec.deviceSelector.driver`、`pool`、`device` 与 taint effect。
- 输出契约：HTTP Warning response header，文本必须与公开需求一致。
- PR 未声明 schema、存储版本、数据库迁移或埋点变化。

## 8. 风险与兼容性

- 最大风险是把 `soft_prompt` 错升为 `hard_block`，导致兼容性破坏。
- nil 与 `{}` 的语义必须区分，否则会对合法的省略场景产生噪声。
- 客户端的 warnings-as-errors 行为容易被误判为服务端创建失败，需要同时核对对象状态。
- 多条警告并存时的去重和顺序可能影响客户端断言。

## 9. 待确认问题

- driver/pool/device 组合为空字符串或只含空白时如何判定？
- patch、apply、status 子资源是否属于“update”覆盖范围？
- 同一请求产生多条 warning 时，顺序与去重规则是什么？
- Warning header 的标准编码/agent 文本拼接是否已有公共约束？

## 10. 本轮整理边界

- 本摘要只冻结公开 PR 描述中的行为契约，不采用实现路径、测试和现场验证 Oracle，也不在本阶段生成 Structured PRD、Case Plan 或测试用例。
