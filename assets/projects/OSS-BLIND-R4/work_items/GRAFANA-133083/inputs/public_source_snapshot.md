# GRAFANA-133083 公开需求快照

- 来源：https://github.com/grafana/grafana/pull/133083
- 标题：APIStore: Allow explicit serializer
- 状态：已合并
- 目标分支：`main`
- 作者：`ryantxu`
- 冻结日期：2026-09-22

## 可作为需求输入的行为事实

- 同一个 Go 类型可能被多个 GVK 共用，资源需要控制持久化 JSON 的序列化方式。
- APIStore 需要支持可显式配置、可感知请求上下文的 Serializer，并一致覆盖写入、读取、列表和 watch。
- 未显式配置时：声明 GVK 的写入沿用直接 JSON；其他写入使用已配置 codec；读取使用已配置 codec。
- 显式 Serializer 应覆盖默认选择。
- datasource 的通用 JSON Serializer 需要保留 GVK。
- watch 解码需要保留原请求上下文和取消语义。
- datasource 专用 Serializer 与转换逻辑属于后续工作。

## 盲测隔离

本快照不包含代码 diff、提交内容、实现路径、自动化测试、Review 评论或作者验证结果。上述信息仅允许在后续 Oracle 阶段使用。
