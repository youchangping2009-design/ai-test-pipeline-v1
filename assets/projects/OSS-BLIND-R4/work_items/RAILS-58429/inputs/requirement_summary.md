# RAILS-58429 BroadcastLogger tagged semantics across multiple loggers 需求整理

整理时间：2026-09-22

## 1. 资料来源

- Rails GitHub PR #58429 的公开描述与合并元数据。
- 本地冻结快照：`inputs/public_source_snapshot.md`。
- 为保持盲测，代码 diff、辅助方法、现有测试和 Review 评论不作为需求输入。

## 2. 需求结论

- `BroadcastLogger#tagged` 在多个广播 logger 下应保持单一 logger 的可用语义：无 block 时返回可继续记录消息的 BroadcastLogger；有 block 时只 yield 一次，并使所有支持 tagged 的 logger 在 block 内带标签，异常退出后也完成清理。

## 3. 前置条件 / 准备工作

- BroadcastLogger 至少包含两个广播目标。
- 覆盖多个支持 tagged 的 logger，以及支持/不支持 tagged 混合的组合。
- 分别覆盖有 block、无 block和 block 抛异常的调用方式。

## 4. 业务范围与不做范围

- 范围内：`BroadcastLogger#tagged` 的返回类型、消息广播、block 执行次数、标签激活与清理、混合能力 logger 的兼容。
- 范围外：改变单个 logger 的 tagged 实现、改变日志格式、引入新的日志级别或修改不相关的广播 API。

## 5. 面向研发的需求拆解

- 无 block 调用必须返回可调用 `info` 等日志方法的 BroadcastLogger，而不是 logger 结果集合。
- 返回对象中的支持 tagged 的 logger 应带指定标签。
- 不支持 tagged 的广播目标不得因此丢失，后续消息仍应发送给它们。
- 有 block 调用只执行一次用户 block，执行期间所有支持 tagged 的 logger 均处于标签上下文。
- block 正常结束或抛出异常后，临时标签都必须被清理。

## 6. 面向测试的验收关注点

- 两个支持 tagged 的 logger：无 block 返回对象可继续写日志，两个目标均收到带标签消息。
- 支持与不支持 tagged 的混合组合：无 block 后所有目标仍收到消息，仅支持者应用标签。
- 有 block 时计数证明 block 只执行一次，所有支持者在同一次执行中带标签。
- block 抛异常时异常继续传播，随后写日志不再携带临时标签。
- 单个支持 tagged 的 logger 和既有常规广播行为不回退。
- 嵌套 tagged 调用的标签顺序和清理应保持一致。

## 7. 数据 / 埋点 / 接口 / 配置要求

- 关键公开 API：`BroadcastLogger#tagged` 与其 block/非 block 两种调用形式。
- logger 是否参与标签处理以 `respond_to?(:tagged)` 为能力判断。
- PR 未声明新增配置、持久化数据、外部接口或埋点。

## 8. 风险与兼容性

- 返回对象如果遗漏非 tagging logger，会造成静默日志丢失。
- block 重复执行可能重复业务副作用，属于高风险兼容问题。
- 异常路径清理不完整会把标签泄漏到后续请求或线程。
- 嵌套标签、并发日志和不同 logger 返回值可能暴露组合边界。

## 9. 待确认问题

- 零个或一个广播目标时的返回语义是否需要额外约束？
- 无 block 返回的新对象与原对象之间的身份和后续增删广播目标行为如何定义？
- 嵌套标签的精确顺序与重复标签规则是什么？
- 标签上下文的线程/纤程隔离由 BroadcastLogger 还是各 logger 保证？

## 10. 本轮整理边界

- 本摘要只基于公开 PR 描述冻结需求语义，不采用具体实现和测试 Oracle，也不在本阶段生成 Structured PRD、Case Plan 或测试用例。
