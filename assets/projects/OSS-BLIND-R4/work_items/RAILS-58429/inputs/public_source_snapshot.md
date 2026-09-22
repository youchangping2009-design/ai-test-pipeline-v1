# RAILS-58429 公开需求快照

- 来源：https://github.com/rails/rails/pull/58429
- 标题：Fix BroadcastLogger#tagged when broadcasting to multiple tagging loggers
- 状态：已合并
- 目标分支：`main`
- 作者：`ousamabenyounes`
- 冻结日期：2026-09-22

## 可作为需求输入的行为事实

- BroadcastLogger 同时包含多个支持 tagged 的 logger 时，无 block 调用当前可能返回 Array，导致后续日志方法不可用。
- 无 block 形式应返回可继续调用日志方法的 BroadcastLogger，为支持 tagged 的 logger 加标签，并保留不支持 tagged 的广播目标接收消息。
- block 形式当前可能按 logger 多次执行 block；目标是只执行一次，并在执行期间让全部支持 tagged 的 logger 激活标签。
- block 抛出异常时也必须清理标签。
- 是否支持标签以 logger 是否响应 `tagged` 为边界。

## 盲测隔离

本快照不包含代码 diff、具体辅助方法、测试文件、测试结果、提交或 Review 评论。上述信息仅允许在后续 Oracle 阶段使用。
