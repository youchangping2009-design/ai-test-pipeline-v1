# GRAFANA-133083 APIStore explicit serializer 需求整理

整理时间：2026-09-22

## 1. 资料来源

- Grafana GitHub PR #133083 的公开描述与合并元数据。
- 本地冻结快照：`inputs/public_source_snapshot.md`。
- 为保持盲测，代码 diff、提交、Review 评论和新增测试不作为需求输入。

## 2. 需求结论

- APIStore 应允许资源显式提供可感知请求上下文的 Serializer，并在写入、读取、列表和 watch 中使用一致的选择规则。未提供时必须保持现有默认序列化行为，datasource 的通用 JSON Serializer 还需保留 GVK。

## 3. 前置条件 / 准备工作

- 资源可能以同一个 Go 类型承载多个 GVK。
- APIStore 已有声明 GVK、已配置 codec，以及读写、列表和 watch 路径。
- watch 请求具有需要继续传播的 context 与取消信号。

## 4. 业务范围与不做范围

- 范围内：Serializer 的显式配置、默认回退、各存取路径的一致使用、GVK 保留及 watch 上下文传播。
- 范围外：datasource 专用 Serializer、额外转换逻辑、新增 UI，以及重新定义 codec 本身的版本转换规则。

## 5. 面向研发的需求拆解

- APIStore 提供可选的、接收请求上下文的 Serializer 能力。
- 显式 Serializer 在写入、读取、列表和 watch 中均优先于默认路径。
- 未显式配置时，声明 GVK 的写入继续使用直接 JSON，其他写入使用配置 codec，读取继续使用配置 codec。
- datasource 通用 JSON Serializer 的往返处理不得丢失 GVK。
- watch 中当前对象和历史对象的解码不得脱离原请求 context 或屏蔽取消信号。

## 6. 面向测试的验收关注点

- 未配置 Serializer 时，声明 GVK 与非声明 GVK 分别遵循既定写入路径。
- 未配置 Serializer 时，读取、列表和 watch 仍使用既定 codec，旧行为不回退。
- 配置 Serializer 后，写入、单条读取、列表和 watch 均走该 Serializer。
- 同一 Go 类型承载不同 GVK 时，持久化和读回后仍可区分目标 GVK。
- datasource 通用 JSON 往返后保留原 GVK。
- watch 被取消时，解码工作能够观察取消并停止，不能使用脱离请求的后台上下文。

## 7. 数据 / 埋点 / 接口 / 配置要求

- 关键契约：Serializer、配置 codec、声明 GVK、请求 context。
- PR 未声明新增外部 API 字段、数据库迁移、埋点或用户配置界面。

## 8. 风险与兼容性

- 默认分支若发生变化，可能破坏既有资源的存储格式兼容性。
- 列表或 watch 中混合版本/GVK 的对象可能暴露选择不一致。
- 错误的上下文传播可能导致取消失效、资源泄漏或请求结束后继续解码。
- 显式 Serializer 与 codec 的职责边界不清时可能出现双重转换。

## 9. 待确认问题

- Serializer 返回错误、空结果或不支持目标 GVK 时的正式错误契约是什么？
- Serializer 实例是否要求并发安全，生命周期由谁管理？
- 列表/watch 中遇到单个坏对象时，是整体失败还是允许部分结果？
- 版本上限及转换失败的精确规则尚未由公开需求定义。

## 10. 本轮整理边界

- 本摘要只冻结公开 PR 描述中的需求行为；不读取或转述实现与测试 Oracle，也不在本阶段生成 Structured PRD、Case Plan 或测试用例。
